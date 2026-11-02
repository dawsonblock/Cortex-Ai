//! Experimental online curriculum scheduler, independent of final-test tasks.
//!
//! Uses only training attempts (solved, measured candidate expansions) as
//! low-fidelity utility feedback. A success or reduced training search cost is
//! not evidence of transfer, intelligence, or causal concept value.
//! Deterministic UCB-style exploration, limited to two tasks per family.
use std::collections::BTreeMap;
use crate::learning::NamedTask;

#[derive(Debug, Default, Clone, Copy)]
struct TaskHistory { attempts: u64, solved: bool, ever_solved: bool, built: u64 }
#[derive(Debug, Default, Clone, Copy)]
struct FamilyHistory { attempts: u64, reward_sum: f64 }

#[derive(Debug, Default)]
pub(crate) struct AdaptiveCurriculum {
    tasks: BTreeMap<String, TaskHistory>,
    families: BTreeMap<String, FamilyHistory>,
    total_attempts: u64,
}

fn family(task: &str) -> &str { task.split('_').next().unwrap_or(task) }

impl AdaptiveCurriculum {
    /// Record a *training* task result. Reward is deliberately bounded to
    /// [0,1]. Reward a task for its first-ever successful solve, not for
    /// repeatedly recovering from a regression. Reduced search work can earn
    /// a reward only when the task was solved on consecutive attempts.
    /// This is training feedback, not evidence of transfer.
    pub(crate) fn observe(&mut self, id: &str, solved: bool, built: u64) {
        let old = self.tasks.get(id).copied().unwrap_or_default();
        let reward = if solved && !old.ever_solved { 1.0 }
            else if solved && old.solved && old.built > 0 && built < old.built {
                ((old.built - built) as f64 / old.built as f64).min(1.0)
            } else { 0.0 };
        self.tasks.insert(id.to_owned(), TaskHistory {
            attempts: old.attempts.saturating_add(1), solved,
            ever_solved: old.ever_solved || solved, built,
        });
        let fam = self.families.entry(family(id).to_owned()).or_default();
        fam.attempts = fam.attempts.saturating_add(1);
        fam.reward_sum += reward;
        self.total_attempts = self.total_attempts.saturating_add(1);
    }

    fn score(&self, id: &str) -> f64 {
        let task = self.tasks.get(id).copied().unwrap_or_default();
        let fam = self.families.get(family(id)).copied().unwrap_or_default();
        let mean = (0.5 + fam.reward_sum) / (1.0 + fam.attempts as f64);
        let explore = (2.0 * (2.0 + self.total_attempts as f64).ln()
                       / (1.0 + fam.attempts as f64)).sqrt();
        let frontier = if task.attempts == 0 { 2.0 }
                       else if !task.solved { 1.25 } else { 0.3 };
        let hard = (1.0 + task.built as f64).ln().min(14.0) * 0.05;
        let retries = (1.0 + task.attempts as f64).ln() * 0.4;
        1.4 * mean + explore + frontier + hard - retries
    }

    pub(crate) fn select<'a>(&self, tasks: &'a [NamedTask], cap: usize) -> Vec<&'a NamedTask> {
        if cap == 0 { return Vec::new(); }
        let mut ranked: Vec<(f64, &NamedTask)> = tasks.iter()
            .map(|task| (self.score(&task.0), task)).collect();
        ranked.sort_by(|a,b| b.0.total_cmp(&a.0).then_with(|| a.1.0.cmp(&b.1.0)));
        let mut counts = BTreeMap::<&str,usize>::new();
        let mut selected = Vec::new();
        for (_, task) in ranked {
            let entry = counts.entry(family(&task.0)).or_default();
            if *entry == 2 { continue; }
            *entry += 1;
            selected.push(task);
            if selected.len() >= cap { break; }
        }
        selected
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Vec<NamedTask> {
        let t = crate::parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        ["a_0", "a_1", "a_2", "b_0", "c_0"].iter()
            .map(|id| (id.to_string(),t.clone())).collect()
    }
    #[test] fn deterministic_selection_and_family_limit() {
        let p = AdaptiveCurriculum::default();
        let ts = fixture();
        let a = p.select(&ts,4).iter().map(|x| x.0.clone()).collect::<Vec<_>>();
        let b = p.select(&ts,4).iter().map(|x| x.0.clone()).collect::<Vec<_>>();
        assert_eq!(a,b);
        assert_eq!(a.iter().filter(|n|n.starts_with("a_")).count(),2);
    }
    #[test] fn successful_learning_has_higher_family_reward_than_failure() {
        let mut p = AdaptiveCurriculum::default();
        p.observe("a_0",true,200);
        p.observe("b_0",false,200);
        assert!(p.families["a"].reward_sum > p.families["b"].reward_sum);
    }
    #[test] fn decreased_work_is_rewarded_but_regressions_are_not() {
        let mut p=AdaptiveCurriculum::default();
        p.observe("a_0",true,1000);
        let first=p.families["a"].reward_sum;
        p.observe("a_0",true,500);
        assert!((p.families["a"].reward_sum-first-0.5).abs()<1e-12);
        p.observe("a_0",true,800);
        assert_eq!(p.families["a"].reward_sum,first+0.5);
    }
    #[test] fn select_never_uses_unseen_task_sets() {
        let mut p=AdaptiveCurriculum::default();
        p.observe("secret_final",true,1);
        let ts=fixture();
        assert!(p.select(&ts,5).iter().all(|t|!t.0.contains("final")));
    }
    #[test] fn regression_then_recovery_does_not_fabricate_first_solve_reward() {
        let mut p = AdaptiveCurriculum::default();
        p.observe("a_0", true, 100);
        assert_eq!(p.families["a"].reward_sum, 1.0);
        p.observe("a_0", false, 250);
        p.observe("a_0", true, 90);
        // Earlier versions paid a second +1 just for recovering a lost solve.
        assert_eq!(p.families["a"].reward_sum, 1.0);
        assert!(p.tasks["a_0"].ever_solved);
    }
    #[test] fn first_solve_after_failed_trials_is_rewarded_exactly_once() {
        let mut p = AdaptiveCurriculum::default();
        p.observe("a_0", false, 400);
        p.observe("a_0", false, 300);
        p.observe("a_0", true, 150);
        assert_eq!(p.families["a"].reward_sum, 1.0);
        p.observe("a_0", true, 120);
        assert!((p.families["a"].reward_sum - 1.2).abs() < 1e-12);
    }
    #[test] fn unresolved_task_never_receives_efficiency_reward() {
        let mut p = AdaptiveCurriculum::default();
        p.observe("a_0", false, 400);
        p.observe("a_0", false, 1);
        assert_eq!(p.families["a"].reward_sum, 0.0);
    }
    #[test] fn empty_cap_is_safe() {
        assert!(AdaptiveCurriculum::default().select(&fixture(),0).is_empty());
    }
}
