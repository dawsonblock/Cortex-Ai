//! Deterministic shared candidate-expansion budget allocator.
//!
//! Zero is the bank's "unbounded" sentinel. Never return zero as a composed
//! limit when the caller has requested a bounded search and a nonzero reserve.
//! In legacy/unbounded mode the reserve is disabled and existing behavior stays.

/// Time left after a concept-first attempt and its verification. The caller
/// must not start raw enumeration with a zero allowance; 0 is an exhausted
/// deadline, never an instruction to run without limits.
pub(crate) fn remaining_time_secs(total: f64, elapsed: std::time::Duration) -> f64 {
    if !total.is_finite() || total <= 0.0 { return 0.0; }
    (total - elapsed.as_secs_f64()).max(0.0)
}

/// Maximum work allowed to concept-first search, with an opt-in reserve for
/// verified raw fallback. A positive reserve and total>=2 imply [1,total-1].
pub(crate) fn composed_limit(total: u64, reserve_pct: u8) -> u64 {
    if total == 0 || reserve_pct == 0 { return total; }
    let reserve = ((total as u128 * reserve_pct as u128 + 99) / 100) as u64;
    total.saturating_sub(reserve.max(1).min(total.saturating_sub(1)))
}

/// Remaining shared budget after concept search; zero means no budget remains
/// when total > 0, rather than an unbounded search.
pub(crate) fn fallback_limit(total: u64, concept_built: u64) -> u64 {
    if total == 0 { 0 } else { total.saturating_sub(concept_built) }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn shared_time_is_work_conserving_and_exhaustible() {
        use std::time::Duration;
        assert!((remaining_time_secs(1.0, Duration::from_millis(250)) - 0.75).abs() < 1e-12);
        assert_eq!(remaining_time_secs(0.2, Duration::from_millis(200)), 0.0);
        assert_eq!(remaining_time_secs(0.2, Duration::from_millis(250)), 0.0);
        assert_eq!(remaining_time_secs(f64::NAN, Duration::ZERO), 0.0);
        assert_eq!(remaining_time_secs(f64::INFINITY, Duration::ZERO), 0.0);
    }
    #[test]
    fn reserved_fraction_keeps_raw_path_alive() {
        assert_eq!(composed_limit(100, 25), 75);
        assert_eq!(fallback_limit(100, 75), 25);
        assert_eq!(fallback_limit(100, 20), 80);
        assert_eq!(composed_limit(7, 25), 5); // ceil(1.75)=2
        assert_eq!(composed_limit(2, 95), 1);
    }
    #[test]
    fn opt_in_preserves_old_behavior() {
        assert_eq!(composed_limit(123, 0), 123);
        assert_eq!(composed_limit(0, 0), 0);
        assert_eq!(fallback_limit(0, 9), 0);
        assert_eq!(fallback_limit(50, 51), 0);
    }
    #[test]
    fn large_limits_do_not_overflow() {
        let total = u64::MAX;
        let cap = composed_limit(total, 95);
        assert!(cap > 0 && cap < total);
        assert_eq!(fallback_limit(total, cap), total-cap);
    }
    #[test]
    fn shared_budget_invariant() {
        for total in 2..200 {
            for percentage in 1..=95 {
                let cap = composed_limit(total, percentage);
                assert!(cap >= 1 && cap < total);
                for actual in [0, cap/2, cap] {
                    let remaining = fallback_limit(total, actual);
                    assert!(remaining >= 1);
                    assert_eq!(remaining.saturating_add(actual), total);
                }
            }
        }
    }
}
