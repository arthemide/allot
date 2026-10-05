# Vendored woob modules

woob fetches its bank modules from a remote repository by default. To keep
Allot fully local (no third-party call at runtime), the `boursorama` module
and anything it needs are vendored here instead.

Populate this directory once, from a machine with network access, by copying
the modules from a woob checkout or release (GPL/LGPL, kept with their own
licence headers):

    cp -r <woob-checkout>/modules/boursorama vendor/woob-modules/

`make connectors-install` then points woob at `../woob-sources.list` so these
are the only modules it knows about.
