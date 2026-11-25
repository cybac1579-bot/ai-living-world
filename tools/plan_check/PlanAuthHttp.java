package com.ailivingworld.mobile;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.net.UnknownHostException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLException;

/** Send OAuth forms with Android's default trust store and hostname verification. */
public final class PlanAuthHttp {
    private PlanAuthHttp() {}

    public static String[] request(String address, String form, int timeoutMillis) {
        HttpsURLConnection connection = null;
        try {
            URL url = new URL(address);
            if (!"https".equals(url.getProtocol()) || !"auth.openai.com".equals(url.getAuthority())
                    || url.getRef() != null || (form != null && !address.equals(
                    "https://auth.openai.com/api/accounts/oauth/token"))) {
                return new String[]{"endpoint", ""};
            }
            connection = (HttpsURLConnection) url.openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setUseCaches(false);
            connection.setConnectTimeout(timeoutMillis);
            connection.setReadTimeout(timeoutMillis);
            connection.setRequestProperty("Accept", "application/json");
            if (form != null) {
                byte[] data = form.getBytes(StandardCharsets.UTF_8);
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(data.length);
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(data);
                }
            }
            int status = connection.getResponseCode();
            try (InputStream input = status >= 400 ? connection.getErrorStream() : connection.getInputStream()) {
                if (input == null) return new String[]{Integer.toString(status), ""};
                ByteArrayOutputStream body = new ByteArrayOutputStream();
                byte[] bytes = new byte[4096];
                int count;
                while ((count = input.read(bytes)) != -1) {
                    if (body.size() + count > 256 * 1024) return new String[]{"size", ""};
                    body.write(bytes, 0, count);
                }
                return new String[]{Integer.toString(status), body.toString("UTF-8")};
            }
        } catch (UnknownHostException ex) {
            return new String[]{"dns", ""};
        } catch (SSLException ex) {
            return new String[]{"tls", ""};
        } catch (SocketTimeoutException ex) {
            return new String[]{"timeout", ""};
        } catch (IOException ex) {
            return new String[]{"network", ""};
        } finally {
            if (connection != null) connection.disconnect();
        }
    }
}
