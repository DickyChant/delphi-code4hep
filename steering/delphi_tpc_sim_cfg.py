import os

import FWCore.ParameterSet.Config as cms
from FWCore.Modules.modules import EmptySource
from Code4hep.G4Application.modules import G4SimProducer
from Code4hep.Generators.modules import GenProducer

process = cms.Process("DELPHITPC")
process.source = EmptySource()
process.maxEvents.input = int(os.environ.get("C4H_MAX_EVENTS", "1"))
process.options.numberOfThreads = 1
process.options.numberOfStreams = 1

process.gen = GenProducer(
    generatorType=cms.string("HepMC3Generator"),
    generator=cms.InputTag("MCParticles"),
    initialSeed=cms.uint32(12345),
    Verbosity=cms.untracked.int32(0),
    PartID=cms.untracked.int32(13),
    MinPt=cms.double(10.0),
    MaxPt=cms.double(10.0),
    MinEta=cms.double(-2.5),
    MaxEta=cms.double(2.5),
    MinPhi=cms.double(-3.14159265359),
    MaxPhi=cms.double(3.14159265359),
)

process.sim = G4SimProducer(
    generator=cms.InputTag("gen", "MCParticles"),
    randomSeed=cms.uint32(67890),
    Physics=cms.PSet(type=cms.string("FTFP_BERT")),
    Detector=cms.PSet(
        gdml=cms.string(os.environ["C4H_GDML"]),
        magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
    ),
)

process.tpcPads = cms.EDProducer(
    "delphi_edm4hep::DelphiTpcPadMapperProducer",
    simTrackerHits=cms.InputTag("sim", "SimTrackerHits"),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
)

process.tpcDigis = cms.EDProducer(
    "delphi_edm4hep::DelphiTpcDigitizerProducer",
    simTrackerHits=cms.InputTag("sim", "SimTrackerHits"),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
    randomSeed=cms.uint32(24680),
    electronEnergyEv=cms.double(20.0),
    avalancheScale=cms.double(0.016),
    magneticFieldTesla=cms.double(float(os.environ["C4H_FIELD_TESLA"])),
)

process.tpcHits = cms.EDProducer(
    "delphi_edm4hep::DelphiTpcHitReconstructionProducer",
    digis=cms.InputTag("tpcDigis", "TpcDigis"),
    digiTruthLinks=cms.InputTag(
        "tpcDigis", "TpcDigiSimTrackerHitLinks"
    ),
    cargoSnapshot=cms.string(os.environ["C4H_DELPHI_CARGO"]),
)

process.output = cms.OutputModule(
    "PodioOutputModule",
    fileName=cms.untracked.string(os.environ["C4H_OUTPUT"]),
)

process.generation_step = cms.Path(process.gen)
process.simulation_step = cms.Path(process.sim)
process.tpc_mapping_step = cms.Path(process.tpcPads)
process.tpc_digitization_step = cms.Path(process.tpcDigis)
process.tpc_reconstruction_step = cms.Path(process.tpcHits)
process.output_step = cms.EndPath(process.output)
process.schedule = cms.Schedule(
    process.generation_step,
    process.simulation_step,
    process.tpc_mapping_step,
    process.tpc_digitization_step,
    process.tpc_reconstruction_step,
    process.output_step,
)
