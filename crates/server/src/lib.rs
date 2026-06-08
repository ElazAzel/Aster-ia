/// Asterion AI cloud server.
///
/// Phase 3: axum-based HTTP server with:
/// - JWT auth
/// - Multi-tenant rate limiting
/// - GPU cluster routing
/// - Usage metering + Stripe billing
/// - Same API surface as desktop (single codebase via asterion-core)

pub mod routes;
pub mod auth;
