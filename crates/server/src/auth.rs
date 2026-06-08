/// JWT authentication for cloud server.
/// Phase 3: implement JWT validation, tier checks, API key management.

pub struct JwtConfig {
    pub secret: String,
    pub issuer: String,
}
