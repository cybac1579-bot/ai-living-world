package com.ailivingworld.mobile;

import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.*;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.*;
import java.util.Date;
import org.junit.Test;
import static org.junit.Assert.*;

public class PlanIdentityTest {
    @Test public void bindsIdentityToIssuerKeyAccountAndAttempt() throws Exception {
        RSAKey key = new RSAKeyGenerator(2048).keyID("fixture").generate();
        String keys = new JWKSet(key.toPublicJWK()).toString();
        long now = System.currentTimeMillis();
        JWTClaimsSet base = new JWTClaimsSet.Builder().issuer("https://auth.openai.com").subject("fixture")
                .audience("client").issueTime(new Date(now-1000)).expirationTime(new Date(now+60000))
                .claim("nonce","attempt").build();
        String token = sign(base,key);
        assertEquals("fixture", PlanIdentity.verify(token,"client","attempt",keys));
        assertThrows(Exception.class, () -> PlanIdentity.verify(token,"other","attempt",keys));
        assertThrows(Exception.class, () -> PlanIdentity.verify(token,"client","other",keys));
        assertThrows(Exception.class, () -> PlanIdentity.verify(new PlainJWT(base).serialize(),"client","attempt",keys));
        String expired = sign(new JWTClaimsSet.Builder(base).expirationTime(new Date(now-10000)).build(),key);
        assertThrows(Exception.class, () -> PlanIdentity.verify(expired,"client","attempt",keys));
        String otherKeys = new JWKSet(new RSAKeyGenerator(2048).keyID("fixture").generate().toPublicJWK()).toString();
        assertThrows(Exception.class, () -> PlanIdentity.verify(token,"client","attempt",otherKeys));
    }

    private static String sign(JWTClaimsSet claims, RSAKey key) throws Exception {
        SignedJWT jwt = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).keyID("fixture").build(),claims);
        jwt.sign(new RSASSASigner(key));
        return jwt.serialize();
    }
}
