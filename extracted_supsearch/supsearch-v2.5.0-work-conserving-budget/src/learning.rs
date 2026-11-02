//! Governed, bounded concept acquisition for the raw-lambda synthesizer.
//!
//! All acquisition decisions use development tasks. Training tasks produce
//! candidate abstractions. Final-test tasks are read only once, after all
//! promotions. Nothing in this module claims proof of general correctness.
//! No LLM output, candidate file, or mining result has promotion authority.
use crate::{bank, bootstrap, parse, term};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

pub(crate) type NamedTask = (String, parse::Task);

#[derive(Debug, Clone)]
struct Config {
    directory: PathBuf,
    train: Vec<String>,
    dev: Vec<String>,
    test: Vec<String>,
    library: PathBuf,
    ledger: PathBuf,
    candidates: Option<PathBuf>,
    rounds: usize,
    budget: f64,
    max_size: u32,
    top_tasks: usize,
    max_candidates: usize,
    max_arity: u32,
    min_gain_pct: f64,
    max_regression_pct: f64,
    fuel: i64,
    max_built: u64,
    // Percentage of the bounded search reserved for verified raw fallback.
    raw_reserve_pct: u8,
    // Share the time allowance between concept-first and raw fallback.
    shared_time_budget: bool,
    require_native_mined: bool,
    // Zero keeps v1.8 exploratory admission behavior. Positive values
    // activate a conservative expansion-count amortization filter.
    expected_reuses: u64,
    // Optional training-corpus compression and development-family gates.
    min_mdl_gain: u64,
    min_positive_families: usize,
    curriculum_policy: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            directory: PathBuf::from("bench"),
            train: Vec::new(), dev: Vec::new(), test: Vec::new(),
            library: PathBuf::from("out/learning/concepts.tsv"),
            ledger: PathBuf::from("out/learning/decisions.jsonl"),
            candidates: None, rounds: 3, budget: 1.0, max_size: 13,
            top_tasks: 4, max_candidates: 8, max_arity: 5,
            min_gain_pct: 0.10, max_regression_pct: 0.15, fuel: 20_000,
            max_built: 0, raw_reserve_pct: 0, shared_time_budget: true, require_native_mined: false, expected_reuses: 0,
            min_mdl_gain: 0, min_positive_families: 0,
            curriculum_policy: "heuristic".to_owned(),
        }
    }
}

fn parse_list(s: &str) -> Vec<String> {
    s.split(',').map(str::trim).filter(|x| !x.is_empty()).map(str::to_owned).collect()
}

fn parse_options(args: &[String]) -> Result<Config, String> {
    let mut c = Config::default();
    let mut i = 0;
    while i < args.len() {
        let flag = args[i].as_str();
        if !flag.starts_with("--") && i == 0 {
            c.directory = PathBuf::from(flag);
            i += 1;
            continue;
        }
        let val = args.get(i + 1).ok_or_else(|| format!("missing value for {flag}"))?;
        match flag {
            "--train" => c.train = parse_list(val),
            "--dev" => c.dev = parse_list(val),
            "--test" => c.test = parse_list(val),
            "--library" => c.library = PathBuf::from(val),
            "--ledger" => c.ledger = PathBuf::from(val),
            "--candidates" => c.candidates = Some(PathBuf::from(val)),
            "--rounds" => c.rounds = val.parse().map_err(|_| "invalid rounds")?,
            "--budget" => c.budget = val.parse().map_err(|_| "invalid budget")?,
            "--max-size" => c.max_size = val.parse().map_err(|_| "invalid max-size")?,
            "--top-tasks" => c.top_tasks = val.parse().map_err(|_| "invalid top-tasks")?,
            "--max-candidates" => c.max_candidates = val.parse().map_err(|_| "invalid max-candidates")?,
            "--max-arity" => c.max_arity = val.parse().map_err(|_| "invalid max-arity")?,
            "--min-gain-pct" => c.min_gain_pct = val.parse().map_err(|_| "invalid min-gain-pct")?,
            "--max-regression-pct" => c.max_regression_pct = val.parse().map_err(|_| "invalid max-regression-pct")?,
            "--fuel" => c.fuel = val.parse().map_err(|_| "invalid fuel")?,
            "--max-built" => c.max_built = val.parse().map_err(|_| "invalid max-built")?,
            "--raw-reserve-pct" => c.raw_reserve_pct = val.parse().map_err(|_| "invalid raw-reserve-pct")?,
            "--shared-time-budget" => c.shared_time_budget = match val.as_str() {
                "true" => true, "false" => false,
                _ => return Err("invalid shared-time-budget (true|false)".into()),
            },
            "--expected-reuses" => c.expected_reuses = val.parse().map_err(|_| "invalid expected-reuses")?,
            "--min-mdl-gain" => c.min_mdl_gain = val.parse().map_err(|_| "invalid min-mdl-gain")?,
            "--min-positive-families" => c.min_positive_families = val.parse().map_err(|_| "invalid min-positive-families")?,
            "--curriculum-policy" => c.curriculum_policy = val.clone(),
            "--require-native-mined" => c.require_native_mined = match val.as_str() {
                "true" => true, "false" => false, _ => return Err("invalid require-native-mined (true|false)".into()),
            },
            _ => return Err(format!("unknown learn flag {flag}")),
        }
        i += 2;
    }
    if c.train.is_empty() || c.dev.is_empty() {
        return Err("--train and --dev must both contain task IDs".into());
    }
    if c.rounds == 0 || c.rounds > 100 || c.top_tasks == 0 || c.max_candidates == 0
        || c.max_arity == 0 || c.max_arity > 5 || c.max_size < 2 || c.max_size > 64
        || c.top_tasks > 128 || c.max_candidates > 128 || c.max_built > 100_000_000 || c.expected_reuses > 1_000_000
        || c.min_mdl_gain > 1_000_000 || c.min_positive_families > 128
        || c.raw_reserve_pct > 95
        || (c.raw_reserve_pct > 0 && c.max_built < 2) || c.fuel <= 0 || c.fuel > 10_000_000
        || !c.budget.is_finite() || c.budget <= 0.0 || c.budget > 3600.0
        || !matches!(c.curriculum_policy.as_str(), "heuristic" | "adaptive")
        || !c.min_gain_pct.is_finite() || !(0.0..=1.0).contains(&c.min_gain_pct)
        || !c.max_regression_pct.is_finite() || !(0.0..=10.0).contains(&c.max_regression_pct)
    {
        return Err("invalid learning limits, budget, or admission threshold".into());
    }
    if c.require_native_mined && c.candidates.is_some() {
        return Err("native-mined-only mode forbids imported candidate files".into());
    }
    if c.ledger == c.library { return Err("ledger and library cannot be the same file".into()); }
    let mut seen = BTreeSet::new();
    for (split, ids) in [("train", &c.train), ("dev", &c.dev), ("test", &c.test)] {
        for id in ids {
            if id.is_empty() || !id.chars().all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-') {
                return Err(format!("unsafe task ID: {id:?}"));
            }
            if !seen.insert(id.clone()) {
                return Err(format!("task {id:?} appears in multiple splits or twice in {split}"));
            }
        }
    }
    Ok(c)
}

pub(crate) fn load_tasks(dir: &Path, ids: &[String]) -> Result<Vec<NamedTask>, String> {
    ids.iter().map(|id| {
        let p = dir.join(format!("{id}.tsk"));
        // Bounded file read: do not let an untrusted task exhaust the process
        // before parser validation. The evaluator still requires OS isolation
        // from hostile peers able to swap files after the metadata check.
        let meta = fs::symlink_metadata(&p).map_err(|e| format!("{}: {e}", p.display()))?;
        if !meta.file_type().is_file() || meta.len() > 2 * 1024 * 1024 {
            return Err(format!("{}: unsafe or oversized task", p.display()));
        }
        let file = fs::File::open(&p).map_err(|e| format!("{}: {e}", p.display()))?;
        let mut bytes = Vec::new();
        file.take(2 * 1024 * 1024 + 1).read_to_end(&mut bytes)
            .map_err(|e| format!("{}: {e}", p.display()))?;
        if bytes.len() > 2 * 1024 * 1024 {
            return Err(format!("{}: task grew beyond 2 MiB", p.display()));
        }
        let s = String::from_utf8(bytes).map_err(|e| format!("{}: {e}", p.display()))?;
        let t = parse::parse_task(id, &s)
            .map_err(|e| format!("{id}: {e:?}"))?;
        if t.tests.is_empty() || t.arity == 0 {
            return Err(format!("{id}: empty task or zero arguments not accepted"));
        }
        Ok((id.to_owned(), t))
    }).collect()
}

fn is_closed(t: &term::Term, depth: u32) -> bool {
    match t {
        term::Term::Var(i) => *i < depth,
        term::Term::Lam(b) => is_closed(b, depth + 1),
        term::Term::App(f,a) => is_closed(f, depth) && is_closed(a, depth),
        term::Term::Free(_) | term::Term::Prim(_) => false,
    }
}

/// Expand previously admitted `Prim` atoms when using concept-composed
/// solutions as the next mining corpus. Refuse unbounded expansion.
fn expand_prim(t: &Rc<term::Term>, remaining: &mut usize) -> Option<Rc<term::Term>> {
    if *remaining == 0 { return None; }
    *remaining -= 1;
    match t.as_ref() {
        term::Term::Prim(body) => expand_prim(body, remaining),
        term::Term::Lam(body) => Some(term::lam(expand_prim(body, remaining)?)),
        term::Term::App(f,a) => Some(term::app(expand_prim(f, remaining)?,expand_prim(a, remaining)?)),
        _ => Some(t.clone()),
    }
}

fn parse_candidate(line: &str) -> Result<Rc<term::Term>, String> {
    // A candidate is a closed lambda expression. No raw code or commands.
    if line.len() > 16_384 { return Err("candidate is too long".into()); }
    let e = parse::parse_expr(line)?;
    let t = parse::to_term(&e)?;
    if !is_closed(&t, 0) { return Err("candidate is not closed".into()); }
    if t.size() > 512 { return Err("candidate has more than 512 AST nodes".into()); }
    Ok(t)
}

fn load_candidate_file(path: &Path) -> Result<Vec<Rc<term::Term>>, String> {
    // Do not follow a symlink to a candidate file with a different provenance.
    // Metadata is rechecked before bounded reading; adversarial concurrent
    // mutation still requires OS filesystem isolation.
    let meta = fs::symlink_metadata(path).map_err(|e| format!("{}: {e}", path.display()))?;
    if !meta.file_type().is_file() || meta.len() > 2 * 1024 * 1024 {
        return Err("unsafe or oversized candidate input".into());
    }
    let mut file = fs::File::open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut bytes = Vec::new();
    file.take(2 * 1024 * 1024 + 1).read_to_end(&mut bytes)
        .map_err(|e| format!("{}: {e}", path.display()))?;
    if bytes.len() > 2 * 1024 * 1024 { return Err("candidate input grew beyond 2 MiB".into()); }
    let content = String::from_utf8(bytes).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut terms = Vec::new();
    for (i, line) in content.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with("//") || line.starts_with('#') { continue; }
        terms.push(parse_candidate(line).map_err(|e| format!("{}:{}: {e}", path.display(), i+1))?);
    }
    Ok(terms)
}

pub(crate) fn load_library(path: &Path) -> Result<Vec<bank::Concept>, String> {
    if !path.exists() { return Ok(Vec::new()); }
    let md = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    if !md.file_type().is_file() || md.len() > 2 * 1024 * 1024 {
        return Err("unsafe or oversized concept library".into());
    }
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    let mut names = BTreeSet::new();
    let mut bodies = BTreeSet::new();
    for (i, line) in text.lines().enumerate() {
        if line.is_empty() || line.starts_with('#') { continue; }
        let mut fields = line.splitn(3, '\t');
        let name = fields.next().unwrap_or("");
        let arity: u32 = fields.next().unwrap_or("").parse()
            .map_err(|_| format!("{}:{}: invalid arity", path.display(), i + 1))?;
        let src = fields.next().ok_or_else(|| format!("{}:{}: missing concept", path.display(),i+1))?;
        if name.is_empty() || name.len() > 96 || !name.chars().all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-') || arity == 0 || arity > 5 {
            return Err(format!("{}:{}: invalid concept header", path.display(),i+1));
        }
        let body = parse_candidate(src)?;
        if !names.insert(name.to_owned()) || !bodies.insert(term::show(&body)) {
            return Err(format!("{}:{}: duplicate concept name or body", path.display(), i + 1));
        }
        if out.len() >= 256 { return Err("concept library exceeds 256 entries".into()); }
        out.push(bank::Concept { body, name: name.to_owned(), arity });
    }
    Ok(out)
}

fn persist_library(path: &Path, concepts: &[bank::Concept]) -> Result<(), String> {
    let mut data = String::from("# supsearch learn v1; name<TAB>composition arity<TAB>closed lambda expression\n");
    for c in concepts {
        data.push_str(&format!("{}\t{}\t{}\n", c.name, c.arity, term::show(&c.body)));
    }
    atomic_write(path, data.as_bytes())
}

pub(crate) fn atomic_write(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let temp = path.with_extension(format!("tmp-{}", std::process::id()));
    // Never truncate or follow a preexisting temporary path. A stale temporary
    // file must cause a fail-closed error rather than damage unrelated data.
    let mut f = fs::OpenOptions::new().write(true).create_new(true).open(&temp)
        .map_err(|e| format!("temporary concept-library path unavailable: {e}"))?;
    let res = (|| -> Result<(), String> {
        f.write_all(bytes).map_err(|e| e.to_string())?;
        f.sync_all().map_err(|e| e.to_string())?;
        fs::rename(&temp, path).map_err(|e| e.to_string())?;
        Ok(())
    })();
    if res.is_err() { let _ = fs::remove_file(&temp); }
    res
}

/// Write an immutable result through a complete sibling temporary file.
/// Hard-link creation atomically fails when the final path already exists,
/// avoiding a check-then-rename race and leaving the old result unchanged.
/// This is cooperative filesystem safety, not hostile-process isolation.
pub(crate) fn atomic_write_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let temp = path.with_extension(format!("tmp-new-{}", std::process::id()));
    // Fail if the temp path is preexisting. Only unlink temp files this process
    // successfully created; never remove another process's stale file.
    let mut file = fs::OpenOptions::new().write(true).create_new(true).open(&temp)
        .map_err(|e| format!("create temporary result: {e}"))?;
    let outcome = (|| -> Result<(), String> {
        file.write_all(bytes).map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        fs::hard_link(&temp, path).map_err(|e| format!("result already exists or cannot be installed: {e}"))?;
        Ok(())
    })();
    let _ = fs::remove_file(&temp);
    outcome
}

pub(crate) fn json_escape(s: &str) -> String {
    let mut out = String::from("\"");
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if ch < ' ' => out.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

fn append_ledger(path: &Path, line: &str) -> Result<(), String> {
    if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let mut f = fs::OpenOptions::new().create(true).append(true).open(path).map_err(|e| e.to_string())?;
    writeln!(f, "{line}").map_err(|e| e.to_string())?;
    f.sync_all().map_err(|e| e.to_string())
}

fn unix_time() -> u64 { SystemTime::now().duration_since(UNIX_EPOCH).map_or(0, |d| d.as_secs()) }

fn bank_options(c: &Config) -> bank::Options {
    let mut o = bank::Options::default();
    o.max_size = c.max_size;
    o.time_budget_secs = c.budget;
    o.fuel = c.fuel;
    o.max_built = c.max_built;
    o
}

/// Re-evaluate the closed synthesized program on every supplied example.
/// The solver uses behavioral hashes to accelerate discovery; this checks
/// the actual normal forms with a separate application-and-normalization path.
/// This is finite-example consistency, NOT proof for arbitrary inputs.
pub(crate) fn solution_matches_examples(task: &parse::Task, solution: &Rc<term::Term>, fuel: i64) -> bool {
    if fuel <= 0 || task.tests.is_empty() { return false; }
    let empty: crate::nbe::Env = Rc::new(Vec::new());
    for example in &task.tests {
        if example.args.len() != task.arity { return false; }
        let mut candidate = solution.clone();
        for arg in &example.args {
            candidate = term::app(candidate, arg.clone());
        }
        let mut actual_fuel = crate::nbe::Fuel(fuel);
        let actual = match crate::nbe::normalize(&empty, &candidate, &mut actual_fuel) {
            Ok(value) => value,
            Err(_) => return false,
        };
        let mut expected_fuel = crate::nbe::Fuel(fuel);
        let expected = match crate::nbe::normalize(&empty, &example.want, &mut expected_fuel)
            .ok().and_then(|nf| parse::strip_outer(&nf, example.outer)) {
            Some(value) => value,
            None => return false,
        };
        if actual != expected { return false; }
    }
    true
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Measure { solved: bool, built: u64 }

fn measure(task: &parse::Task, concepts: &[bank::Concept], opts: &bank::Options) -> Measure {
    let o = bank::concept_solve(task, concepts, opts);
    Measure { solved: o.solution.as_ref().is_some_and(|sol| solution_matches_examples(task, sol, opts.fuel)), built: o.stats.built }
}

fn measure_set(tasks: &[NamedTask], concepts: &[bank::Concept], opts: &bank::Options) -> Vec<Measure> {
    tasks.iter().map(|(_,t)| measure(t, concepts, opts)).collect()
}

/// Prefer a composed solution only after an independent finite-example check.
/// If absent OR invalid, run raw enumeration. The caller separately adds
/// `composed_built` so failed composition and subsequent raw work are both
/// charged to the training attempt. This is not a formal proof.
fn verified_or_raw_fallback<F>(
    task: &parse::Task,
    composed: Option<Rc<term::Term>>,
    fuel: i64,
    raw_solver: F,
) -> (Option<Rc<term::Term>>, u64, &'static str)
where
    F: FnOnce() -> bank::Outcome,
{
    if let Some(program) = composed {
        if solution_matches_examples(task, &program, fuel) {
            return (Some(program), 0, "composed");
        }
    }
    let outcome = raw_solver();
    // Never put a failed raw solution into the mining corpus either.
    let valid_raw = outcome.solution.filter(|program| solution_matches_examples(task, program, fuel));
    (valid_raw, outcome.stats.built, "raw")
}

#[derive(Clone, Debug)]
struct Evidence {
    new_solved: usize,
    lost_solved: usize,
    severe_regressions: usize,
    improvement: f64,
    // Paired work savings include only tasks solved by BOTH libraries.
    // Unlocked tasks count toward ability, but not amortization.
    paired_savings: i128,
    baseline_solved: usize,
    candidate_solved: usize,
    accepted: bool,
}

fn compare(before: &[Measure], after: &[Measure], min_gain: f64, max_regression: f64) -> Evidence {
    assert_eq!(before.len(), after.len());
    let mut new_solved = 0;
    let mut lost_solved = 0;
    let mut severe_regressions = 0;
    let mut baseline_solved = 0;
    let mut candidate_solved = 0;
    let mut before_cost = 0f64;
    let mut after_cost = 0f64;
    let mut paired_savings: i128 = 0;
    for (b,a) in before.iter().zip(after) {
        if b.solved { baseline_solved += 1; }
        if a.solved { candidate_solved += 1; }
        if !b.solved && a.solved { new_solved += 1; }
        if b.solved && !a.solved { lost_solved += 1; }
        if b.solved && a.solved {
            let old = b.built.max(1) as f64;
            let new = a.built.max(1) as f64;
            if new > old * (1.0 + max_regression) && new - old > 2.0 { severe_regressions += 1; }
            before_cost += old;
            after_cost += new;
            paired_savings += b.built as i128 - a.built as i128;
        }
    }
    let improvement = if before_cost > 0.0 { (before_cost - after_cost) / before_cost } else { 0.0 };
    Evidence {
        new_solved, lost_solved, severe_regressions, improvement, paired_savings,
        baseline_solved, candidate_solved,
        accepted: lost_solved == 0 && severe_regressions == 0 &&
            (new_solved > 0 || (baseline_solved > 0 && improvement >= min_gain)),
    }
}

/// Count development task families with at least one newly unlocked solution
/// or a net positive expansion saving among tasks solved in both arms.
/// Family labels come from task IDs; this is NOT independently held-out transfer.
fn positive_development_families(
    dev: &[NamedTask], before: &[Measure], after: &[Measure],
) -> usize {
    assert_eq!(dev.len(), before.len());
    assert_eq!(dev.len(), after.len());
    let mut gains = BTreeMap::<String, (u64, i128)>::new();
    for ((id,_), (b,a)) in dev.iter().zip(before.iter().zip(after.iter())) {
        let item = gains.entry(family(id).to_owned()).or_insert((0,0));
        if !b.solved && a.solved { item.0 += 1; }
        if b.solved && a.solved { item.1 += b.built as i128 - a.built as i128; }
    }
    gains.values().filter(|(new, savings)| *new > 0 || *savings > 0).count()
}

#[derive(Clone)]
struct Proposal {
    body: Rc<term::Term>, arity: u32, evidence: Evidence,
    origin: &'static str, mdl_gain: i64, positive_families: usize,
}

fn preferred(a: &Proposal, b: &Proposal) -> bool {
    // Lexicographic: unlocked tasks first, then saved successful-search work.
    (a.evidence.new_solved, (a.evidence.improvement * 1_000_000.0) as i64)
        > (b.evidence.new_solved, (b.evidence.improvement * 1_000_000.0) as i64)
}

fn try_candidate(
    body: &Rc<term::Term>, current: &[bank::Concept], dev: &[NamedTask],
    before: &[Measure], opts: &bank::Options, cfg: &Config, origin: &'static str,
    mdl_gain: i64,
) -> (Vec<Proposal>, Vec<(u32, Evidence, u64, usize)>) {
    let mut viable: Vec<Proposal> = Vec::new();
    let mut trials = Vec::new();
    for arity in 1..=cfg.max_arity {
        let mut augmented = current.to_vec();
        augmented.push(bank::Concept { body: body.clone(), name: "trial".into(), arity });
        let after = measure_set(dev, &augmented, opts);
        let ev = compare(before, &after, cfg.min_gain_pct, cfg.max_regression_pct);
        let trial_built = after.iter().map(|m| m.built).sum::<u64>();
        let positive_families = positive_development_families(dev, before, &after);
        trials.push((arity, ev.clone(), trial_built, positive_families));
        if !ev.accepted { continue; }
        let proposed = Proposal { body: body.clone(), arity, evidence: ev, origin,
                                  mdl_gain, positive_families };
        viable.push(proposed);
    }
    (viable, trials)
}

fn family(id: &str) -> &str { id.split('_').next().unwrap_or(id) }

/// Lightweight learning-priority model: allocate search effort to unsolved
/// frontiers, then to computationally expensive successes. Attempts reduce
/// priority to prevent retrying the same hopeless task forever. Diversity is
/// enforced by at most two tasks from a family per round.
fn choose_tasks<'a>(tasks: &'a [NamedTask], history: &BTreeMap<String, (usize, Measure)>, cap: usize) -> Vec<&'a NamedTask> {
    let mut scored: Vec<(f64, &NamedTask)> = tasks.iter().map(|nt| {
        let (attempts, m) = history.get(&nt.0).copied().unwrap_or((0, Measure { solved: false, built: 0 }));
        let frontier = if m.solved { 1.0 } else { 4.0 };
        let difficulty = ((m.built + 1) as f64).ln_1p().min(12.0);
        ((frontier + difficulty) / (1.0 + attempts as f64), nt)
    }).collect();
    scored.sort_by(|a,b| b.0.total_cmp(&a.0).then_with(|| a.1.0.cmp(&b.1.0)));
    let mut counts = BTreeMap::<String, usize>::new();
    let mut chosen = Vec::new();
    for (_, task) in scored {
        let n = counts.entry(family(&task.0).to_owned()).or_default();
        if *n >= 2 { continue; }
        chosen.push(task);
        *n += 1;
        if chosen.len() >= cap { break; }
    }
    chosen
}


/// Structural finite-example identity from parsed lambda terms. Binder names
/// disappear in the de Bruijn representation, so alpha-renamed examples are
/// identified even when task titles, whitespace or headers differ. This is NOT
/// full beta/eta equivalence and is NOT a semantic proof of dataset separation.
fn example_keys(task: &parse::Task) -> BTreeSet<String> {
    task.tests.iter().map(|test| {
        let args = test.args.iter().map(|arg| term::show(arg)).collect::<Vec<_>>();
        format!("arity={} outer={} args={:?} want={}",
                task.arity, test.outer, args, term::show(&test.want))
    }).collect()
}

fn reject_cross_split_examples(train: &[NamedTask], dev: &[NamedTask]) -> Result<(), String> {
    let mut train_examples = BTreeMap::<String, String>::new();
    for (id, task) in train {
        for key in example_keys(task) {
            train_examples.entry(key).or_insert_with(|| id.clone());
        }
    }
    for (id, task) in dev {
        for key in example_keys(task) {
            if let Some(source_id) = train_examples.get(&key) {
                return Err(format!("train/dev structurally duplicate example: {source_id} and {id}"));
            }
        }
    }
    Ok(())
}

fn run_inner(args: &[String]) -> Result<(), String> {
    let cfg = parse_options(args)?;
    let task_dir = fs::canonicalize(&cfg.directory).map_err(|e| format!("task directory: {e}"))?;
    for protected in [&cfg.library, &cfg.ledger] {
        if protected.components().any(|part|matches!(part,std::path::Component::ParentDir)) {
            return Err("learning output cannot contain parent traversal".into());
        }
        let parent = protected.parent().filter(|p| !p.as_os_str().is_empty())
            .unwrap_or_else(|| Path::new("."));
        let mut ancestor = parent;
        while !ancestor.exists() {
            ancestor = ancestor.parent().ok_or("cannot resolve output directory")?;
        }
        let resolved_parent = fs::canonicalize(ancestor).map_err(|e|e.to_string())?
            .join(parent.strip_prefix(ancestor).map_err(|e|e.to_string())?);
        if resolved_parent.starts_with(&task_dir) {
            return Err("output library and ledger must live outside task input directory".into());
        }
        if let Ok(full) = fs::canonicalize(protected) {
            if full.starts_with(&task_dir) {
                return Err("output aliases task input directory".into());
            }
        }
    }
    let train = load_tasks(&cfg.directory, &cfg.train)?;
    let dev = load_tasks(&cfg.directory, &cfg.dev)?;
    // Refuse exact duplicate development/training task files even under different IDs.
    for tid in &cfg.train {
        let ta = fs::read(cfg.directory.join(format!("{tid}.tsk"))).map_err(|e| e.to_string())?;
        for did in &cfg.dev {
            let tb = fs::read(cfg.directory.join(format!("{did}.tsk"))).map_err(|e| e.to_string())?;
            if ta == tb { return Err(format!("train/dev exact duplicate content: {tid} and {did}")); }
        }
    }
    // Compare actual parsed test structures, not merely file bytes or IDs.
    reject_cross_split_examples(&train, &dev)?;
    // Do not even open final-test examples before concept selection ends.
    let external = if let Some(path) = &cfg.candidates { load_candidate_file(path)? } else { Vec::new() };
    // Single-writer guard covers the complete training and promotion session.
    // Stale locks are deliberately not auto-recovered: investigate a crash first.
    // It is cooperative and requires a trusted local filesystem, not a hostile
    // multi-user security boundary.
    let _run_lock = crate::journal::RunLock::acquire(&cfg.ledger)?;
    let mut library = load_library(&cfg.library)?;
    // A strict, bounded top-level JSONL parser rejects forged event-name
    // substrings, duplicate JSON keys, incomplete lines and orphan commits.
    // Reconcile the last recorded native commit with the actual library.
    crate::journal::verify_history(&cfg.ledger, &library)?;
    // Materialize an empty baseline even when the learning round admits nothing;
    // downstream auditors must not infer a missing library is an empty library.
    if !cfg.library.exists() { persist_library(&cfg.library, &library)?; }
    // Immutable in-memory pre-learning control for terminal paired evaluation.
    let starting_library = library.clone();
    if library.len().saturating_add(cfg.rounds) > 256 {
        return Err("planned promotions would exceed 256 concepts".into());
    }
    let opts = bank_options(&cfg);
    let mut observed = BTreeMap::<String, (usize, Measure)>::new();
    let mut adaptive = crate::curriculum::AdaptiveCurriculum::default();
    let mut corpus = Vec::<Rc<term::Term>>::new();
    let mut trained = BTreeSet::<String>::new();
    let mut attempted = BTreeSet::<String>::new();
    let mut seen = BTreeSet::<String>::new();
    for concept in &library { seen.insert(term::show(&concept.body)); }
    let mut mined_opts = bootstrap::MineOptions::default();
    mined_opts.per_round = cfg.max_candidates;
    println!("learn: {} train / {} dev / {} sealed-test; {} existing concepts; budget {}s",
        train.len(), dev.len(), cfg.test.len(), library.len(), cfg.budget);
    append_ledger(&cfg.ledger, &format!(
        "{{\"event\":\"start\",\"schema_version\":8,\"ts\":{},\"train\":{},\"dev\":{},\"test\":{},\"initial_concepts\":{},\"max_built\":{},\"rounds\":{},\"expected_reuses\":{},\"min_mdl_gain\":{},\"min_positive_families\":{},\"curriculum_policy\":{},\"raw_reserve_pct\":{},\"shared_time_budget\":{},\"time_budget_secs\":{:.9}}}",
        unix_time(),train.len(),dev.len(),cfg.test.len(),library.len(),cfg.max_built,cfg.rounds,cfg.expected_reuses,
        cfg.min_mdl_gain,cfg.min_positive_families,json_escape(&cfg.curriculum_policy),cfg.raw_reserve_pct,cfg.shared_time_budget,cfg.budget))?;
    for round in 0..cfg.rounds {
        let mut round_train_built: u64 = 0;
        let mut round_trial_built: u64 = 0;
        println!("round {round}: prioritizing training frontier");
        let selected = if cfg.curriculum_policy == "adaptive" {
            adaptive.select(&train, cfg.top_tasks)
        } else {
            choose_tasks(&train, &observed, cfg.top_tasks)
        };
        // One immutable selection event precedes all training attempts in the
        // round. No development or final-test outcomes enter the selector.
        let selected_ids = selected.iter().map(|t| t.0.as_str()).collect::<Vec<_>>().join(",");
        append_ledger(&cfg.ledger, &format!(
            "{{\"event\":\"curriculum_selection\",\"round\":{},\"policy\":{},\"tasks\":{}}}",
            round, json_escape(&cfg.curriculum_policy), json_escape(&selected_ids)))?;
        for (id, task) in selected {
            let attempt_start = Instant::now();
            // After the first promotion, try learning *through* concepts.
            // Fall back to raw enumeration if the concept composer cannot solve.
            let composed_cap = if library.is_empty() { 0 } else {
                crate::search_budget::composed_limit(cfg.max_built, cfg.raw_reserve_pct)
            };
            let (composed_solution, composed_built) = if library.is_empty() {
                (None, 0u64)
            } else {
                let mut concept_options = bank_options(&cfg);
                // A nonzero reserve cannot be disabled by passing max_built=0:
                // zero means UNBOUNDED to the underlying bank.
                concept_options.max_built = composed_cap;
                let out = bank::concept_solve(task, &library, &concept_options);
                (out.solution, out.stats.built)
            };
            let composed_elapsed_secs = attempt_start.elapsed().as_secs_f64();
            let mut raw_time_limit_secs = 0.0_f64;
            let mut raw_elapsed_secs = 0.0_f64;
            // A syntactically present composed solution can still fail the
            // independent finite-example recheck. In both failure cases
            // (None and Some(invalid)) retry raw enumeration and count its
            // work; do not silently skip the fallback.
            let raw_limit = crate::search_budget::fallback_limit(cfg.max_built, composed_built);
            let (solution, raw_built, search_kind) = verified_or_raw_fallback(
                task, composed_solution, cfg.fuel, || {
                    let mut raw_options = bank_options(&cfg);
                    // Both phases share one elapsed clock. A remaining-time
                    // value of zero is exhausted, NOT an unbounded sentinel.
                    let raw_seconds = if cfg.shared_time_budget {
                        crate::search_budget::remaining_time_secs(cfg.budget, attempt_start.elapsed())
                    } else {
                        cfg.budget
                    };
                    raw_time_limit_secs = raw_seconds;
                    if raw_seconds <= 0.0 {
                        return bank::Outcome {
                            solution: None, stats: bank::Stats::default(),
                        };
                    }
                    raw_options.time_budget_secs = raw_seconds;
                    if cfg.max_built > 0 {
                        if raw_limit == 0 {
                            // Exhausted the shared candidate-expansion budget.
                            return bank::Outcome {
                                solution: None, stats: bank::Stats::default(),
                            };
                        }
                        raw_options.max_built = raw_limit;
                    }
                    let raw_start = Instant::now();
                    let outcome = bank::solve(task, &raw_options);
                    raw_elapsed_secs = raw_start.elapsed().as_secs_f64();
                    outcome
                }
            );
            // Include failed concept-search work before raw fallback. This
            // measures candidate expansions, not wall time or miner overhead.
            let built = composed_built.saturating_add(raw_built);
            round_train_built = round_train_built.saturating_add(built);
            let m = Measure { solved: solution.as_ref().is_some_and(|sol| solution_matches_examples(task, sol, cfg.fuel)), built };
            let attempts = observed.get(id).map_or(0, |(a,_)| *a);
            observed.insert(id.clone(), (attempts + 1, m));
            adaptive.observe(id, m.solved, m.built);
            attempted.insert(id.clone());
            if let Some(sol) = solution.filter(|sol| solution_matches_examples(task, sol, cfg.fuel)) {
                if trained.insert(id.clone()) {
                    let mut remaining = 4096usize;
                    if let Some(expanded) = expand_prim(&sol, &mut remaining) {
                        corpus.push(expanded);
                    }
                }
            }
            append_ledger(&cfg.ledger, &format!(
                "{{\"event\":\"train_attempt\",\"round\":{},\"task\":{},\"kind\":{},\"solved\":{},\"built\":{},\"composed_built\":{},\"raw_built\":{},\"composed_limit\":{},\"raw_limit\":{},\"composed_elapsed_secs\":{:.9},\"raw_time_limit_secs\":{:.9},\"raw_elapsed_secs\":{:.9},\"wall_elapsed_secs\":{:.9}}}",
                round,json_escape(id),json_escape(search_kind),m.solved,m.built,composed_built,raw_built,composed_cap,raw_limit,
                composed_elapsed_secs,raw_time_limit_secs,raw_elapsed_secs,attempt_start.elapsed().as_secs_f64()))?;
            println!("  train {id}: mode={search_kind} solved={} built={}",m.solved,m.built);
        }
        let train_args: Vec<Rc<term::Term>> = train.iter()
            .filter(|(id,_)| trained.contains(id))
            .flat_map(|(_,t)| t.tests.iter())
            .flat_map(|t| t.args.iter().cloned()).collect();
        let mut proposals = Vec::<(Rc<term::Term>, &'static str)>::new();
        if !corpus.is_empty() && !train_args.is_empty() {
            let grouping = bootstrap::build_grouping_pool(&train_args, 0x5eed_0000 + round as u64);
            let probes = bootstrap::build_holdout_pool(0xc0ffee_0000 + round as u64 * 7);
            for mined in bootstrap::mine(&corpus, &grouping, &probes, &mined_opts) {
                proposals.push((mined.comb, "native_mining"));
            }
        }
        // Preserve miner ranking, then imported-candidate order; never allow
        // duplicate bodies to consume the candidate-evaluation quota.
        proposals.extend(external.iter().cloned().map(|body| (body, "imported_candidate")));
        let mut unique = Vec::<(Rc<term::Term>, &'static str)>::new();
        let mut local_seen = BTreeSet::new();
        for (p, origin) in proposals {
            let key = term::show(&p);
            if !seen.contains(&key) && local_seen.insert(key) { unique.push((p, origin)); }
        }
        let baseline = measure_set(&dev, &library, &opts);
        let round_dev_baseline_built: u64 = baseline.iter().map(|m| m.built).sum();
        append_ledger(&cfg.ledger, &format!(
            "{{\"event\":\"dev_baseline_work\",\"round\":{},\"built\":{},\"tasks\":{}}}",
            round,round_dev_baseline_built,baseline.len()))?;
        let mut qualifying = Vec::<Proposal>::new();
        let mut n_evaluated = 0usize;
        for (body, origin) in unique.into_iter().take(cfg.max_candidates) {
            n_evaluated += 1;
            let mdl_gain = crate::mdl::net_gain(&corpus, &body);
            let (proposals, trials) = try_candidate(
                &body, &library, &dev, &baseline, &opts, &cfg, origin, mdl_gain);
            for (arity, ev, trial_built, positive_families) in trials {
                round_trial_built = round_trial_built.saturating_add(trial_built);
                append_ledger(&cfg.ledger, &format!(
                    "{{\"event\":\"candidate_trial\",\"round\":{},\"term\":{},\"origin\":{},\"arity\":{},\"accepted\":{},\"new_solved\":{},\"lost_solved\":{},\"severe_regressions\":{},\"improvement\":{:.6},\"built\":{},\"paired_savings\":{},\"mdl_gain\":{},\"positive_families\":{}}}",
                    round,json_escape(&term::show(&body)),json_escape(origin),arity,ev.accepted,ev.new_solved,
                    ev.lost_solved,ev.severe_regressions,ev.improvement,trial_built,
                    ev.paired_savings,mdl_gain,positive_families))?;
            }
            qualifying.extend(proposals);
        }
        // This forecast includes ALL measured screening work in the current
        // round, even rejected concepts and alternative arities. It is an
        // optimistic lower bound, not a claim of actual CPU-time payback.
        let round_learning_cost = round_train_built.saturating_add(round_dev_baseline_built)
            .saturating_add(round_trial_built);
        let total_qualified = qualifying.len();
        let mut allowed = qualifying.into_iter().filter(|p| {
            crate::reuse_policy::assess(round_learning_cost, p.evidence.paired_savings,
                                        cfg.expected_reuses).is_some()
                && (cfg.min_mdl_gain == 0 || p.mdl_gain >= cfg.min_mdl_gain as i64)
                && p.positive_families >= cfg.min_positive_families
        });
        let mut best = allowed.next();
        for p in allowed {
            if best.as_ref().map_or(true, |prior| preferred(&p, prior)) { best = Some(p); }
        }
        if let Some(selected) = best {
            let ev = &selected.evidence;
            let name = format!("concept_{:04}",library.len()+1);
            let term_src = term::show(&selected.body);
            let added = bank::Concept { body: selected.body.clone(), arity: selected.arity, name: name.clone() };
            let mut new_library = library.clone();
            new_library.push(added);
            // Record intent before updating library. Crash recovery is conservative:
            // rerun will not double-add a library entry, but audit the last event.
            append_ledger(&cfg.ledger, &format!(
                "{{\"event\":\"promotion_intent\",\"ts\":{},\"round\":{},\"name\":{},\"origin\":{},\"arity\":{},\"term\":{},\"new_solved\":{},\"lost_solved\":{},\"severe_regressions\":{},\"improvement\":{:.6},\"baseline_solved\":{},\"candidate_solved\":{},\"paired_savings\":{},\"round_measured_acquisition\":{},\"assumed_reuses\":{},\"mdl_gain\":{},\"positive_families\":{}}}",
                unix_time(),round,json_escape(&name),json_escape(selected.origin),selected.arity,json_escape(&term_src),ev.new_solved,
                ev.lost_solved,ev.severe_regressions,ev.improvement,ev.baseline_solved,ev.candidate_solved,
                ev.paired_savings,round_learning_cost,cfg.expected_reuses,
                selected.mdl_gain,selected.positive_families))?;
            persist_library(&cfg.library, &new_library)?;
            library = new_library;
            seen.insert(term_src);
            append_ledger(&cfg.ledger, &format!(
                "{{\"event\":\"promotion_committed\",\"ts\":{},\"round\":{},\"name\":{},\"concept_count\":{}}}",
                unix_time(),round,json_escape(&name),library.len()))?;
            println!("  ACCEPT {name} / arity {}: dev new solved {}, no losses, improvement {:.1}%",
                selected.arity,ev.new_solved,ev.improvement*100.0);
        } else {
            append_ledger(&cfg.ledger, &format!(
                "{{\"event\":\"no_promotion\",\"ts\":{},\"round\":{},\"evaluated\":{},\"corpus\":{},\"forecast_rejected\":{}}}",
                unix_time(),round,n_evaluated,corpus.len(),total_qualified))?;
            println!("  no concept admitted ({} candidates evaluated)",n_evaluated);
        }
        let measured_built = round_train_built.saturating_add(round_dev_baseline_built)
            .saturating_add(round_trial_built);
        append_ledger(&cfg.ledger, &format!(
            "{{\"event\":\"round_work\",\"round\":{},\"train_built\":{},\"dev_baseline_built\":{},\"dev_trial_built\":{},\"measured_built\":{}}}",
            round,round_train_built,round_dev_baseline_built,round_trial_built,measured_built))?;
    }
    // Open the sealed test data only after training and promotion end.
    if !cfg.test.is_empty() {
        let test = load_tasks(&cfg.directory, &cfg.test)?;
        // Test data is unsealed only here. Reject reuse of any structural
        // example across splits before computing final results.
        reject_cross_split_examples(&train, &test)?;
        reject_cross_split_examples(&dev, &test)?;
        let initial_results = measure_set(&test, &starting_library, &opts);
        let final_results = measure_set(&test, &library, &opts);
        let paired = compare(&initial_results, &final_results,
                             cfg.min_gain_pct, cfg.max_regression_pct);
        append_ledger(&cfg.ledger, &format!(
            "{{\"event\":\"final_test_paired\",\"ts\":{},\"initial_concepts\":{},\"learned_concepts\":{},\"base_solved\":{},\"learned_solved\":{},\"new_solved\":{},\"lost_solved\":{},\"search_cost_improvement\":{:.6},\"internal_test_only\":true}}",
            unix_time(), starting_library.len(), library.len(),
            paired.baseline_solved, paired.candidate_solved,
            paired.new_solved, paired.lost_solved, paired.improvement))?;
        println!("PAIRED INTERNAL TEST (not independent): baseline {} / {} vs learned {} / {}",
                 paired.baseline_solved,test.len(),paired.candidate_solved,test.len());
        let count = final_results.iter().filter(|m| m.solved).count();
        println!("FINAL TEST: {count}/{} solved; concepts {} (not an independent external benchmark)", test.len(),library.len());
        for ((id,_),m) in test.iter().zip(final_results.iter()) {
            append_ledger(&cfg.ledger, &format!(
                "{{\"event\":\"final_test\",\"ts\":{},\"task\":{},\"solved\":{},\"built\":{},\"concepts\":{}}}",
                unix_time(),json_escape(id),m.solved,m.built,library.len()))?;
        }
    }
    // A clean session reaches an explicit terminal record. A crash before this
    // point leaves the journal unrecoverable without manual investigation.
    append_ledger(&cfg.ledger, &format!(
        "{{\"event\":\"session_completed\",\"ts\":{},\"concept_count\":{},\"rounds\":{}}}",
        unix_time(), library.len(), cfg.rounds))?;
    println!("done: {} concepts; {} training tasks attempted; library={}, ledger={}",
        library.len(),attempted.len(),cfg.library.display(),cfg.ledger.display());
    Ok(())
}

pub fn run(args: &[String]) {
    if let Err(e) = run_inner(args) {
        eprintln!("learn error: {e}\nusage: supsearch learn [task-dir] --train id,id --dev id,id [--test id,id] [--candidates FILE] [--rounds 3] [--budget 1] [--max-size 13] [--top-tasks 4] [--max-candidates 8] [--library FILE] [--ledger FILE] [--min-gain-pct 0.1] [--max-regression-pct 0.15] [--max-built N] [--raw-reserve-pct 0..95 (requires max-built>=2)] [--shared-time-budget true|false (default true)] [--expected-reuses N (0=disabled)] [--min-mdl-gain N (0=disabled)] [--min-positive-families N (0=disabled)] [--curriculum-policy heuristic|adaptive]");
        std::process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn m(solved: bool, built: u64) -> Measure { Measure { solved, built } }
    #[test]
    fn optional_compression_and_family_thresholds_parse_safely() {
        let args = ["--train","t","--dev","d","--min-mdl-gain","5",
                    "--min-positive-families","2"].map(str::to_owned);
        let opts = parse_options(&args).unwrap();
        assert_eq!(opts.min_mdl_gain,5);
        assert_eq!(opts.min_positive_families,2);
        assert_eq!(Config::default().min_mdl_gain,0);
        for (flag,value) in [("--min-mdl-gain","1000001"),
                             ("--min-positive-families","129"),
                             ("--min-mdl-gain","-1")] {
            let args = ["--train","t","--dev","d",flag,value].map(str::to_owned);
            assert!(parse_options(&args).is_err());
        }
    }
    #[test]
    fn family_gain_requires_real_local_benefit() {
        let task = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let dev = ["math_1","math_2","lists_1","trees_1"].iter()
            .map(|id| ((*id).to_owned(),task.clone())).collect::<Vec<_>>();
        let before = [m(false,100),m(true,120),m(true,100),m(true,100)];
        let after  = [m(true,120),m(true,130),m(true,90),m(true,120)];
        assert_eq!(positive_development_families(&dev,&before,&after),2);
    }
    #[test]
    fn forecast_option_parses_and_rejects_overflow() {
        let args = ["--train", "a", "--dev", "b", "--expected-reuses", "50"].map(str::to_owned);
        assert_eq!(parse_options(&args).unwrap().expected_reuses, 50);
        let bad = ["--train", "a", "--dev", "b", "--expected-reuses", "1000001"].map(str::to_owned);
        assert!(parse_options(&bad).is_err());
        let invalid = ["--train", "a", "--dev", "b", "--expected-reuses", "-10"].map(str::to_owned);
        assert!(parse_options(&invalid).is_err());
    }
    #[test]
    fn optional_curriculum_policy_is_strict_and_compatible() {
        let good = ["--train", "a", "--dev", "b", "--curriculum-policy", "adaptive"]
            .map(str::to_owned);
        assert_eq!(parse_options(&good).unwrap().curriculum_policy, "adaptive");
        let default_args = ["--train", "a", "--dev", "b"].map(str::to_owned);
        assert_eq!(parse_options(&default_args).unwrap().curriculum_policy, "heuristic");
        let invalid = ["--train", "a", "--dev", "b", "--curriculum-policy", "unknown"]
            .map(str::to_owned);
        assert!(parse_options(&invalid).is_err());
    }
    #[test]
    fn regression_rejection_precedes_economic_forecast() {
        let ev = compare(&[m(true,100)], &[m(false,1)], 0.10, 0.15);
        assert!(!ev.accepted);
        assert_eq!(ev.paired_savings, 0);
        assert!(crate::reuse_policy::assess(100, ev.paired_savings, 10).is_none());
    }
    #[test]
    fn unlocked_task_does_not_fake_paired_cost_savings() {
        let ev = compare(&[m(false, 100)], &[m(true, 1)], 0.10, 0.15);
        assert!(ev.accepted);
        assert_eq!(ev.paired_savings, 0);
        assert!(crate::reuse_policy::assess(10, ev.paired_savings, 5).is_none());
    }
    #[test]
    fn actual_paired_savings_drive_forecast() {
        let ev = compare(&[m(true,100)], &[m(true,70)], 0.10, 0.15);
        assert_eq!(ev.paired_savings, 30);
        assert!(crate::reuse_policy::assess(121, ev.paired_savings, 4).is_none());
        assert_eq!(crate::reuse_policy::assess(121, ev.paired_savings, 5).unwrap().min_reuses, 5);
    }
    #[test]
    fn trial_work_counts_all_development_searches() {
        let example = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let dev = vec![("id".into(), example)];
        let cfg = Config { max_arity: 2, max_size: 4, budget: 0.01, max_built: 200, ..Config::default() };
        let opts = bank_options(&cfg);
        let before = measure_set(&dev, &[], &opts);
        let candidate = parse_candidate("λa.a").unwrap();
        let (_, trial) = try_candidate(&candidate, &[], &dev, &before, &opts, &cfg, "native_mining", 0);
        assert_eq!(trial.len(), 2);
        assert!(trial.iter().all(|(_, _, built, _)| *built <= 200));
    }
    #[test]
    fn invalid_composed_candidate_falls_back_to_raw() {
        use std::cell::Cell;
        let task = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let invalid = parse_candidate("λa.λb.b").unwrap();
        let good = parse_candidate("λa.a").unwrap();
        let raw_ran = Cell::new(false);
        let (solution, built, kind) = verified_or_raw_fallback(&task, Some(invalid), 10_000, || {
            raw_ran.set(true);
            bank::Outcome { solution: Some(good.clone()),
                            stats: bank::Stats { built: 17, ..bank::Stats::default() } }
        });
        assert!(raw_ran.get());
        assert_eq!(kind, "raw");
        assert_eq!(built, 17);
        assert!(solution.as_ref().is_some_and(|v| solution_matches_examples(&task,v,10_000)));
    }
    #[test]
    fn valid_composed_candidate_skips_raw() {
        let task = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let good = parse_candidate("λa.a").unwrap();
        let (solution, built, kind) = verified_or_raw_fallback(&task, Some(good), 10_000, || {
            panic!("raw search must not run when composed solution is valid")
        });
        assert_eq!(kind, "composed");
        assert_eq!(built, 0);
        assert!(solution.is_some());
    }
    #[test]
    fn missing_composed_candidate_falls_back_to_raw() {
        let task = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let good = parse_candidate("λa.a").unwrap();
        let (_, built, kind) = verified_or_raw_fallback(&task, None, 10_000, || {
            bank::Outcome { solution: Some(good),
                            stats: bank::Stats { built: 13, ..bank::Stats::default() } }
        });
        assert_eq!((built, kind), (13, "raw"));
    }
    #[test]
    fn invalid_raw_candidate_not_entered_into_learning_corpus() {
        let task = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let invalid = parse_candidate("λa.λb.b").unwrap();
        let (sol, built, kind) = verified_or_raw_fallback(&task, None, 10_000, || {
            bank::Outcome { solution: Some(invalid),
                            stats: bank::Stats { built: 29, ..bank::Stats::default() } }
        });
        assert!(sol.is_none());
        assert_eq!((built, kind), (29, "raw"));
    }
    #[cfg(unix)]
    #[test]
    fn candidate_file_symlink_is_rejected() {
        use std::os::unix::fs::symlink;
        let p = std::env::temp_dir().join(format!("supsearch-v180-symlink-{}", std::process::id()));
        let target = p.with_extension("real");
        let _ = fs::remove_file(&p);
        fs::write(&target, "λa.a\n").unwrap();
        symlink(&target, &p).unwrap();
        assert!(load_candidate_file(&p).is_err());
        let _ = fs::remove_file(&p);
        let _ = fs::remove_file(&target);
    }
    #[test]
    fn fallback_search_work_is_additive() {
        let composed = 15u64;
        let raw = 27u64;
        assert_eq!(composed.saturating_add(raw), 42);
    }
    #[test]
    fn state_cap_option_is_bounded_and_propagates() {
        let args = ["--train", "a", "--dev", "b", "--max-built", "17"].map(str::to_owned);
        let cfg = parse_options(&args).unwrap();
        assert_eq!(bank_options(&cfg).max_built, 17);
        let args = ["--train", "a", "--dev", "b", "--max-built", "100000001"].map(str::to_owned);
        assert!(parse_options(&args).is_err());
        let args = ["--train", "a", "--dev", "b", "--max-built", "-1"].map(str::to_owned);
        assert!(parse_options(&args).is_err());
    }
    #[test]
    fn native_only_blocks_imported_candidates() {
        let args = ["--train","a","--dev","b","--candidates","candidate.txt",
                    "--require-native-mined","true"].map(str::to_owned);
        assert!(parse_options(&args).is_err());
        let args = ["--train","a","--dev","b","--require-native-mined","invalid"].map(str::to_owned);
        assert!(parse_options(&args).is_err());
    }
    #[test]
    fn recheck_accepts_identity_and_rejects_wrong_program() {
        let task = parse::parse_task("id", "id\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let good = parse_candidate("λa.a").unwrap();
        let bad = parse_candidate("λa.λb.b").unwrap();
        assert!(solution_matches_examples(&task, &good, 10000));
        assert!(!solution_matches_examples(&task, &bad, 10000));
        assert!(!solution_matches_examples(&task, &good, 0));
    }
    #[test]
    fn overlapping_train_final_and_dev_final_examples_rejected() {
        let train = parse::parse_task("train", "train\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let final_task = parse::parse_task("test", "test\n---\nλz.@main(z)\n= λz.z\n").unwrap();
        assert!(reject_cross_split_examples(&[("train".into(), train)],
                                             &[("test".into(), final_task)]).is_err());
    }
    #[test]
    fn rejects_overlapping_splits() {
        let args = vec!["bench", "--train", "a,b", "--dev", "b,c"];
        assert!(parse_options(&args.iter().map(|s|s.to_string()).collect::<Vec<_>>()).is_err());
    }
    #[test]
    fn blocks_solved_to_unsolved_regression() {
        let e = compare(&[m(true,100),m(false,10)], &[m(false,9),m(true,5)], 0.1,0.15);
        assert!(!e.accepted);
        assert_eq!(e.lost_solved,1);
    }
    #[test]
    fn admits_new_solve_without_losses() {
        let e = compare(&[m(true,100),m(false,0)], &[m(true,105),m(true,20)],0.1,0.15);
        assert!(e.accepted);
    }
    #[test]
    fn blocks_expensive_solved_task_regression() {
        let e = compare(&[m(true,100),m(true,20)], &[m(true,150),m(true,15)],0.1,0.15);
        assert!(!e.accepted);
    }
    #[test]
    fn accepts_improved_search_without_new_solve() {
        let e = compare(&[m(true,100)], &[m(true,65)], 0.1,0.15);
        assert!(e.accepted);
    }
    #[test]
    fn candidate_roundtrip() {
        let t = parse_candidate("λa.λb.a(b)").unwrap();
        let s = term::show(&t);
        assert_eq!(t.as_ref(),parse_candidate(&s).unwrap().as_ref());
    }
    #[test]
    fn rejects_unbound_and_ref_candidates() {
        assert!(parse_candidate("a").is_err());
        assert!(parse_candidate("@main").is_err());
    }
    #[test]
    fn task_selection_diversifies_families() {
        let nt = ["a_1", "a_2", "a_3", "b_1"].iter()
            .map(|x| (x.to_string(),parse::Task { tests: vec![], arity: 1 })).collect::<Vec<_>>();
        let chosen = choose_tasks(&nt,&BTreeMap::new(),4);
        assert_eq!(chosen.len(),3);
    }
    #[test]
    fn rejects_untrusted_library_duplicates() {
        let p = std::env::temp_dir().join(format!("supsearch-04-libdup-{}.tsv", std::process::id()));
        fs::write(&p, "first\t2\tλa.λb.a(b)\nfirst\t2\tλa.λb.a(b)\n").unwrap();
        assert!(load_library(&p).is_err());
        fs::write(&p, "first\t2\tλa.λb.a(b)\nsecond\t2\tλa.λb.a(b)\n").unwrap();
        assert!(load_library(&p).is_err());
        fs::write(&p, "bad name\t2\tλa.λb.a(b)\n").unwrap();
        assert!(load_library(&p).is_err());
        let _ = fs::remove_file(&p);
    }
    #[test]
    fn bounds_run_resource_parameters() {
        let args = ["--train","a","--dev","b","--budget","5000"];
        assert!(parse_options(&args.map(str::to_owned)).is_err());
        let args = ["--train","a","--dev","b","--fuel","20000000"];
        assert!(parse_options(&args.map(str::to_owned)).is_err());
    }
    #[test]
    fn alpha_equivalent_train_dev_examples_rejected() {
        let a = parse::parse_task("train", "train\n---\nλa.λb.@main(a,b)\n= λa.λb.a(b)\n").unwrap();
        let b = parse::parse_task("dev", "different header\n---\nλx.λy.@main(x,y)\n= λx.λy.x(y)\n").unwrap();
        let error = reject_cross_split_examples(&[("train".into(),a)], &[("dev".into(),b)]).unwrap_err();
        assert!(error.contains("structurally duplicate"));
    }
    #[test]
    fn different_examples_are_permitted() {
        let a = parse::parse_task("train", "train\n---\nλa.λb.@main(a,b)\n= λa.λb.a(b)\n").unwrap();
        let b = parse::parse_task("dev", "dev\n---\nλx.λy.@main(x,y)\n= λx.λy.y(x)\n").unwrap();
        assert!(reject_cross_split_examples(&[("train".into(),a)], &[("dev".into(),b)]).is_ok());
    }
    #[test]
    fn one_shared_example_in_many_is_rejected() {
        let a = parse::parse_task("train", "train\n---\nλa.@main(a)\n= λa.a\n").unwrap();
        let b = parse::parse_task("dev", "dev\n---\nλx.@main(x)\n= λx.x\nλa.@main(λb.b)\n= λa.λb.b\n").unwrap();
        assert!(reject_cross_split_examples(&[("train".into(),a)], &[("dev".into(),b)]).is_err());
    }
    #[test]
    fn no_clobber_result_is_atomic() {
        let p = std::env::temp_dir().join(format!("supsearch-05-result-{}.txt",std::process::id()));
        let _ = fs::remove_file(&p);
        assert!(atomic_write_new(&p, b"first").is_ok());
        assert!(atomic_write_new(&p, b"second").is_err());
        assert_eq!(fs::read(&p).unwrap(), b"first");
        let _ = fs::remove_file(&p);
    }
    #[test]
    fn atomic_write_refuses_preexisting_temp_without_modifying_it() {
        let dest = std::env::temp_dir().join(format!("supsearch-v210-atomic-{}.tsv",std::process::id()));
        let temp = dest.with_extension(format!("tmp-{}",std::process::id()));
        let _ = fs::remove_file(&dest);
        let _ = fs::remove_file(&temp);
        fs::write(&temp, "valuable-existing-data").unwrap();
        assert!(atomic_write(&dest, b"replacement").is_err());
        assert_eq!(fs::read_to_string(&temp).unwrap(), "valuable-existing-data");
        assert!(!dest.exists());
        fs::remove_file(&temp).unwrap();
        atomic_write(&dest, b"first").unwrap();
        atomic_write(&dest, b"second").unwrap();
        assert_eq!(fs::read(&dest).unwrap(), b"second");
        fs::remove_file(&dest).unwrap();
    }
    #[test]
    fn immutable_write_preserves_preexisting_temp_and_destination() {
        let dest=std::env::temp_dir().join(format!("supsearch-v210-new-{}.jsonl",std::process::id()));
        let temp=dest.with_extension(format!("tmp-new-{}",std::process::id()));
        let _=fs::remove_file(&dest);
        let _=fs::remove_file(&temp);
        fs::write(&temp,b"unowned-temp").unwrap();
        assert!(atomic_write_new(&dest,b"result").is_err());
        assert_eq!(fs::read(&temp).unwrap(),b"unowned-temp");
        assert!(!dest.exists());
        fs::remove_file(&temp).unwrap();
        atomic_write_new(&dest,b"result").unwrap();
        assert!(atomic_write_new(&dest,b"replacement").is_err());
        assert_eq!(fs::read(&dest).unwrap(),b"result");
        let _=fs::remove_file(&dest);
    }
    #[test]
    fn escapes_json_string() {
        assert_eq!(json_escape("a\"\nb"),"\"a\\\"\\nb\"");
    }
}

#[cfg(test)]
mod v240_nonempty_fallback_tests {
    use super::*;

    #[test]
    fn preloaded_concept_cannot_starve_verified_raw_search() {
        // This is the first Rust regression that actually invokes BOTH
        // search algorithms with a nonempty library and a reserved budget.
        // The broader CLI test in scripts/native_reserved_fallback_v240.py
        // separately checks real ledger emission and persistence.
        let task = parse::parse_task("probe_train", include_str!("../bench/ctre_rev.tsk"))
            .expect("parse bundled native test task");
        let body = parse_candidate("λa.λb.λc.b(a(c))").expect("parse bundled concept");
        let concept = bank::Concept {
            name: "probe_seed_mul".to_owned(), arity: 2, body,
        };
        let total = 20u64;
        let cap = crate::search_budget::composed_limit(total, 95);
        assert_eq!(cap, 1);
        let mut compose_opts = bank::Options::default();
        compose_opts.max_built = cap;
        compose_opts.time_budget_secs = 0.2;
        compose_opts.max_size = 4;
        compose_opts.fuel = 1000;
        let composed = bank::concept_solve(&task, &[concept], &compose_opts);
        assert!(composed.stats.built > 0 && composed.stats.built <= cap);
        assert!(composed.solution.is_none(), "the one-step concept allocation must not solve tuple reverse");
        let remaining = crate::search_budget::fallback_limit(total, composed.stats.built);
        assert!(remaining >= 19);
        let mut raw_opts = bank::Options::default();
        raw_opts.max_built = remaining;
        raw_opts.time_budget_secs = 0.2;
        raw_opts.max_size = 4;
        raw_opts.fuel = 1000;
        let (_solution, raw_built, kind) = verified_or_raw_fallback(
            &task, composed.solution, 1000, || bank::solve(&task, &raw_opts));
        assert_eq!(kind, "raw");
        assert!(raw_built > 0);
        assert!(composed.stats.built + raw_built <= total);
    }
}

#[cfg(test)]
mod v230_reserve_tests {
    use super::*;
    #[test]
    fn reserve_option_is_opt_in_and_bounded() {
        let base = ["--train", "a", "--dev", "b"].map(str::to_owned);
        assert_eq!(parse_options(&base).unwrap().raw_reserve_pct, 0);
        let enabled = ["--train", "a", "--dev", "b", "--max-built", "100",
                       "--raw-reserve-pct", "25"].map(str::to_owned);
        assert_eq!(parse_options(&enabled).unwrap().raw_reserve_pct, 25);
        for wrong in ["-1", "96", "100", "garbage"] {
            let args = ["--train", "a", "--dev", "b", "--max-built", "100",
                        "--raw-reserve-pct", wrong].map(str::to_owned);
            assert!(parse_options(&args).is_err());
        }
        let unbounded = ["--train", "a", "--dev", "b", "--raw-reserve-pct", "25"]
            .map(str::to_owned);
        assert!(parse_options(&unbounded).is_err());
        let too_small = ["--train", "a", "--dev", "b", "--max-built", "1",
                         "--raw-reserve-pct", "25"].map(str::to_owned);
        assert!(parse_options(&too_small).is_err());
    }
}

#[cfg(test)]
mod v250_shared_deadline_tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn deadline_is_default_and_explicitly_reversible() {
        let args = ["--train", "a", "--dev", "b"].map(str::to_owned);
        assert!(parse_options(&args).unwrap().shared_time_budget);
        let legacy = ["--train", "a", "--dev", "b", "--shared-time-budget", "false"]
            .map(str::to_owned);
        assert!(!parse_options(&legacy).unwrap().shared_time_budget);
        let invalid = ["--train", "a", "--dev", "b", "--shared-time-budget", "yes"]
            .map(str::to_owned);
        assert!(parse_options(&invalid).is_err());
    }

    #[test]
    fn exhausted_deadline_does_not_invoke_raw_solver() {
        let task = parse::parse_task("deadline_probe", include_str!("../bench/ctre_rev.tsk"))
            .expect("parse task");
        let deadline = Duration::from_secs(1);
        let remaining = crate::search_budget::remaining_time_secs(1.0, deadline);
        let mut invoked = false;
        let (solution, built, kind) = verified_or_raw_fallback(
            &task, None, 1000, || {
                if remaining <= 0.0 {
                    return bank::Outcome {
                        solution: None, stats: bank::Stats::default(),
                    };
                }
                invoked = true;
                bank::Outcome { solution: None, stats: bank::Stats::default() }
            });
        assert!(solution.is_none());
        assert_eq!(built, 0);
        assert_eq!(kind, "raw");
        assert!(!invoked);
    }
}
