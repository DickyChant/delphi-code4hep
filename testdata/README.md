# Native conversion fixture

`pythia8_94c2_one_event.fadana` is the minimal complete prefix needed to read
the first event from a ten-event DELPHI simulation produced with Pythia8 at
91.25 GeV, seed 424244, and the 94C2 processing chain. It is used only as a
technical `delphiRun` CI fixture; it is not a physics reference sample.

The source file was
`pythia8_default_isron_ecm91p25_seed424244_10.fadana` (1,090,560 bytes, SHA-256
`c0790090be73f698714f77ee4edba82f69b273e2ea6bdfa6ed8ebcd12261ca0a`). The fixture contains
its first 155,648 bytes and has SHA-256
`2675244d00c4b900564148d6a9b3d9f54088c6310e1e86c99b299c08c2d8e09c`.
CI deliberately requests exactly one event and does not read the truncated
tail.
