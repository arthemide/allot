/** Whether this browser may talk to the API.
 *
 * Only a password-protected instance guards it, so the front asks at boot
 * rather than assuming either way. */
class Session {
	required = $state(false);
	authenticated = $state(false);
	ready = $state(false);

	/** api.ts, on a 401: the cookie expired. */
	expired() {
		this.authenticated = false;
	}
}

export const session = new Session();
