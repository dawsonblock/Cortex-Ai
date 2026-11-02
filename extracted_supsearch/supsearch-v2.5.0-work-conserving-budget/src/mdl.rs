//! Conservative description-length proxy for candidate abstractions.
//!
//! A closed candidate may replace exact structural subexpressions with one
//! atom. We count the original expression's nodes, the compact expression's
//! nodes, and one copy of the candidate definition plus one library-entry
//! overhead. This is a deliberately narrow compression heuristic, NOT a
//! proof of semantic equivalence or transfer. Prim atoms remain atomic.
use crate::term::Term;
use std::rc::Rc;

fn encoded_size(t: &Term, candidate: &Term) -> u64 {
    if t == candidate { return 1; }
    match t {
        Term::Lam(b) => 1u64.saturating_add(encoded_size(b, candidate)),
        Term::App(f,a) => 1u64.saturating_add(encoded_size(f, candidate))
            .saturating_add(encoded_size(a, candidate)),
        Term::Prim(_) | Term::Var(_) | Term::Free(_) => 1,
    }
}

/// Signed net AST-node savings across this *training* corpus.
/// Positive is a useful secondary signal, not a sufficient promotion rule.
pub(crate) fn net_gain(corpus: &[Rc<Term>], candidate: &Rc<Term>) -> i64 {
    let definition = candidate.size() as u64;
    if definition <= 1 { return -1; }
    let mut saved = 0u64;
    for program in corpus {
        let original = program.size() as u64;
        let compressed = encoded_size(program, candidate);
        saved = saved.saturating_add(original.saturating_sub(compressed));
    }
    let cost = definition.saturating_add(1); // store the definition + one reference
    (saved as i128 - cost as i128).clamp(i64::MIN as i128, i64::MAX as i128) as i64
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::term::{app,lam,var};
    #[test]
    fn repeated_subtree_can_justify_description_length() {
        let concept = lam(app(var(0), var(0)));
        let corpus = vec![concept.clone(),concept.clone(),concept.clone()];
        // 4-node concept, each use saves 3, definition costs 5.
        assert_eq!(net_gain(&corpus, &concept), 4);
    }
    #[test]
    fn absent_concept_is_not_useful() {
        let concept = lam(app(var(0),var(0)));
        let corpus = vec![lam(var(0))];
        assert!(net_gain(&corpus,&concept)<0);
    }
    #[test]
    fn overlap_is_not_double_counted() {
        let concept = lam(app(var(0),var(0)));
        let nested = app(concept.clone(),concept.clone());
        assert_eq!(net_gain(&[nested],&concept), 1);
    }
    #[test]
    fn one_node_candidates_cannot_game_the_gate() {
        let atom = var(0);
        assert!(net_gain(&[atom.clone(),atom.clone()],&atom)<0);
    }
}
