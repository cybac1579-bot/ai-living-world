package com.ailivingworld.mobile;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import com.nimbusds.jose.proc.SecurityContext;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.proc.DefaultJWTClaimsVerifier;
import com.nimbusds.jwt.proc.DefaultJWTProcessor;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashSet;
import java.util.Set;

public final class PlanIdentity {
    private PlanIdentity() {}

    public static String verify(String token, String client, String nonce, String trustedKeys) throws Exception {
        Set<JWSAlgorithm> algorithms = new HashSet<>(Arrays.asList(JWSAlgorithm.RS256, JWSAlgorithm.ES256));
        DefaultJWTProcessor<SecurityContext> processor = new DefaultJWTProcessor<>();
        processor.setJWSKeySelector(new JWSVerificationKeySelector<>(algorithms,
                new ImmutableJWKSet<>(JWKSet.parse(trustedKeys))));
        JWTClaimsSet expected = new JWTClaimsSet.Builder().issuer("https://auth.openai.com")
                .claim("nonce", nonce).build();
        Set<String> required = new HashSet<>(Arrays.asList("sub", "iat", "exp", "aud"));
        DefaultJWTClaimsVerifier<SecurityContext> claims = new DefaultJWTClaimsVerifier<>(
                Collections.singleton(client), expected, required, Collections.emptySet());
        claims.setMaxClockSkew(0);
        processor.setJWTClaimsSetVerifier(claims);
        JWTClaimsSet verified = processor.process(token, null);
        if (verified.getIssueTime().after(new Date()) || verified.getSubject().isEmpty()
                || (verified.getAudience().size() > 1 && !client.equals(verified.getStringClaim("azp")))
                || (verified.getClaim("azp") != null && !client.equals(verified.getStringClaim("azp")))) {
            throw new IllegalArgumentException("Invalid identity claims");
        }
        return verified.getSubject();
    }
}
