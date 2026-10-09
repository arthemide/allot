# Vendored woob modules

woob fetches its bank modules from a remote repository by default. To keep
Allot fully local (no third-party call at runtime), the `boursorama` module
and anything it needs are vendored here instead.

The app loads modules with woob's `WoobBase`, which reads them straight from
this directory and never updates over the network. Fetch and copy the module
once with:

    make woob-install
    make woob-vendor

`make woob-vendor` is the only provisioning step that contacts Woob. Review
and commit the copied module before building an image. To refresh it when
BoursoBank changes its login flow, run it again.

If woob reports a missing sibling module at import time, copy that one too.
