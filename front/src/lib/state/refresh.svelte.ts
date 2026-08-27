/** Bumped whenever something outside the page changes the data.
 *
 * The ticker search lives in the header, so it cannot hand a callback to the
 * page. The page watches this counter instead. */
class Refresh {
	tick = $state(0);

	bump() {
		this.tick += 1;
	}
}

export const refresh = new Refresh();
