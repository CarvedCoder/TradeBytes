/**
 * WebAuthn Browser Helpers
 *
 * Converts between base64url strings (from server JSON) and ArrayBuffers
 * (required by the WebAuthn browser API).
 */

/** Decode a base64url string to a Uint8Array */
function base64urlToBuffer(base64url: string): Uint8Array {
  // Add padding
  const padding = '='.repeat((4 - (base64url.length % 4)) % 4);
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/** Encode an ArrayBuffer to a base64url string */
function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Prepare registration options from server JSON for navigator.credentials.create().
 * Converts base64url strings to ArrayBuffers where the WebAuthn API expects them.
 */
export function prepareRegistrationOptions(options: any): PublicKeyCredentialCreationOptions {
  return {
    ...options,
    challenge: base64urlToBuffer(options.challenge),
    user: {
      ...options.user,
      id: base64urlToBuffer(options.user.id),
    },
    excludeCredentials: (options.excludeCredentials || []).map((cred: any) => ({
      ...cred,
      id: base64urlToBuffer(cred.id),
    })),
  };
}

/**
 * Prepare authentication options from server JSON for navigator.credentials.get().
 */
export function prepareAuthenticationOptions(options: any): PublicKeyCredentialRequestOptions {
  return {
    ...options,
    challenge: base64urlToBuffer(options.challenge),
    allowCredentials: (options.allowCredentials || []).map((cred: any) => ({
      ...cred,
      id: base64urlToBuffer(cred.id),
    })),
  };
}

/**
 * Serialize a registration credential (from navigator.credentials.create())
 * into a JSON-safe object to send to the server.
 */
export function serializeRegistrationCredential(credential: PublicKeyCredential): object {
  const response = credential.response as AuthenticatorAttestationResponse;
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      attestationObject: bufferToBase64url(response.attestationObject),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
    },
  };
}

/**
 * Serialize an authentication credential (from navigator.credentials.get())
 * into a JSON-safe object to send to the server.
 */
export function serializeAuthenticationCredential(credential: PublicKeyCredential): object {
  const response = credential.response as AuthenticatorAssertionResponse;
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      authenticatorData: bufferToBase64url(response.authenticatorData),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
    },
  };
}
