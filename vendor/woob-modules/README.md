# Vendored woob modules

woob fetches its bank modules from a remote repository by default. To keep
Allot fully local (no third-party call at runtime), the `boursorama` module
and anything it needs are vendored here instead.

The app loads modules with woob's `WoobBase`, which reads them straight from
this directory and never updates over the network. So the `boursorama` module
has to be here, fetched once on a machine with network access.

Either from a woob git checkout:

    cp -r <woob-checkout>/modules/boursorama vendor/woob-modules/

or, after `pip install woob && woob update` on that machine:

    make woob-vendor   # copies from $WOOB_MODULES_SRC (default: woob's data dir)

If woob reports a missing sibling module at import time, copy that one too.
