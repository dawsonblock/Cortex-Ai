//! Optional forecast gate for new concept promotions.
//!
//! An estimate, not proof of future reuse or total compute amortization.
//! Inputs are measured candidate expansions; many real costs are unmetered.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Forecast {
    pub min_reuses: u64,
    pub projected_net_expansions: i128,
}

/// `horizon == 0` means the optional economic gate is disabled; callers
/// must still satisfy correctness, solve-rate, and regression requirements.
/// When enabled, the candidate must reduce work on mutually solved tasks
/// and cover all measured acquisition expansions within the assumed horizon.
pub(crate) fn assess(measured_acquisition: u64, paired_savings: i128, horizon: u64) -> Option<Forecast> {
    if horizon == 0 {
        return Some(Forecast { min_reuses: 0, projected_net_expansions: 0 });
    }
    if paired_savings <= 0 { return None; }
    let total = measured_acquisition as i128;
    let min = (total / paired_savings) + i128::from(total % paired_savings != 0);
    if min > horizon as i128 { return None; }
    let net = paired_savings.saturating_mul(horizon as i128).saturating_sub(total);
    Some(Forecast { min_reuses: min as u64, projected_net_expansions: net })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn disabled_preserves_existing_research_policy() {
        assert!(assess(1000, -500, 0).is_some());
    }
    #[test] fn rejects_zero_and_negative_savings() {
        assert!(assess(100, 0, 20).is_none());
        assert!(assess(100, -4, 20).is_none());
    }
    #[test] fn ceiling_is_exact() {
        assert!(assess(101, 10, 10).is_none());
        assert_eq!(assess(101, 10, 11).unwrap().min_reuses, 11);
        assert_eq!(assess(100, 10, 10).unwrap().projected_net_expansions, 0);
    }
    #[test] fn large_values_do_not_overflow() {
        let f = assess(u64::MAX, i128::MAX / 10, 1).unwrap();
        assert!(f.projected_net_expansions > 0);
        assert!(assess(u64::MAX, 1, 1_000_000).is_none());
    }
    #[test] fn zero_acquisition_still_needs_positive_savings() {
        assert_eq!(assess(0, 5, 1).unwrap().min_reuses, 0);
        assert!(assess(0, 0, 1).is_none());
    }
}
