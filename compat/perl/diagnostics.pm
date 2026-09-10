package diagnostics;

# RHEL 9 splits Perl's optional diagnostics pragma from the interpreter.  The
# DELPHI pdl2pdl helper only requests its expanded warning text and does not
# call its API, so a no-op import keeps the legacy parser usable in the native
# integration environment without changing its input or output semantics.
sub import { }

1;
