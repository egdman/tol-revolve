neuron {
  id: "Core-hidden-0"
  layer: "hidden"
  type: "DifferentialCPG"
  partId: "Core"
  param {
    value: -0.159100372048
    name: "bias"
  }
}
neuron {
  id: "Core-hidden-1"
  layer: "hidden"
  type: "DifferentialCPG"
  partId: "Core"
  param {
    value: -0.2114160406
    name: "bias"
  }
}
neuron {
  id: "Leg20Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg20Joint"
  param {
    value: -1
    name: "bias"
  }
  param {
    value: 0.709471415202
    name: "gain"
  }
}
neuron {
  id: "Leg30Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg30Joint"
  param {
    value: -0.673366572948
    name: "bias"
  }
  param {
    value: 0.5
    name: "gain"
  }
}
neuron {
  id: "Leg21Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg21Joint"
  param {
    value: -0.530286833616
    name: "bias"
  }
  param {
    value: 1
    name: "gain"
  }
}
neuron {
  id: "Leg11Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg11Joint"
  param {
    value: 0.723505371555
    name: "bias"
  }
  param {
    value: 0.886677725416
    name: "gain"
  }
}
neuron {
  id: "Core-in-5"
  layer: "input"
  type: "Input"
  partId: "Core"
}
neuron {
  id: "Core-in-4"
  layer: "input"
  type: "Input"
  partId: "Core"
}
neuron {
  id: "Core-in-1"
  layer: "input"
  type: "Input"
  partId: "Core"
}
neuron {
  id: "Core-in-0"
  layer: "input"
  type: "Input"
  partId: "Core"
}
neuron {
  id: "Core-in-3"
  layer: "input"
  type: "Input"
  partId: "Core"
}
neuron {
  id: "Core-in-2"
  layer: "input"
  type: "Input"
  partId: "Core"
}
neuron {
  id: "Leg00Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg00Joint"
  param {
    value: -0.978446422468
    name: "bias"
  }
  param {
    value: 0.404056248074
    name: "gain"
  }
}
neuron {
  id: "Leg31Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg31Joint"
  param {
    value: -0.427962948706
    name: "bias"
  }
  param {
    value: 0.575194285704
    name: "gain"
  }
}
neuron {
  id: "Leg10Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg10Joint"
  param {
    value: 0.198417101332
    name: "bias"
  }
  param {
    value: 0.0188431733919
    name: "gain"
  }
}
neuron {
  id: "Leg01Joint-out-0"
  layer: "output"
  type: "Simple"
  partId: "Leg01Joint"
  param {
    value: 0.533505566985
    name: "bias"
  }
  param {
    value: 0.526639460134
    name: "gain"
  }
}
neuron {
  id: "augment640"
  layer: "hidden"
  type: "DifferentialCPG"
  partId: "Core"
  param {
    value: 0.353524644893
    name: "bias"
  }
}
neuron {
  id: "augment1425"
  layer: "hidden"
  type: "DifferentialCPG"
  partId: "Leg21Joint"
  param {
    value: 0.515250453911
    name: "bias"
  }
}
neuron {
  id: "augment2667"
  layer: "hidden"
  type: "DifferentialCPG"
  partId: "Core"
  param {
    value: 0.179132609652
    name: "bias"
  }
}
connection {
  src: "Core-hidden-0"
  dst: "Core-hidden-1"
  weight: -9.06336713161
  socket: "non_default_socket"
}
connection {
  src: "Core-hidden-1"
  dst: "Leg20Joint-out-0"
  weight: -8.66313594847
}
connection {
  src: "Core-hidden-1"
  dst: "Leg30Joint-out-0"
  weight: -3.70921374228
}
connection {
  src: "Core-hidden-1"
  dst: "Leg21Joint-out-0"
  weight: 17.9072305255
}
connection {
  src: "Core-hidden-1"
  dst: "Leg11Joint-out-0"
  weight: -31.8749496599
}
connection {
  src: "Core-hidden-1"
  dst: "Leg00Joint-out-0"
  weight: -6.76788249409
}
connection {
  src: "Core-hidden-1"
  dst: "Leg31Joint-out-0"
  weight: 4.47684819403
}
connection {
  src: "Core-hidden-1"
  dst: "Leg10Joint-out-0"
  weight: 8.07459020833
}
connection {
  src: "Leg01Joint-out-0"
  dst: "Leg31Joint-out-0"
  weight: -4.87705610607
}
connection {
  src: "Leg20Joint-out-0"
  dst: "Leg20Joint-out-0"
  weight: -4.8910483062
}
connection {
  src: "Core-hidden-1"
  dst: "augment640"
  weight: 0.0911337950821
}
connection {
  src: "augment640"
  dst: "Leg01Joint-out-0"
  weight: 20.4257185985
}
connection {
  src: "Leg00Joint-out-0"
  dst: "Leg11Joint-out-0"
  weight: -18.0088089633
}
connection {
  src: "Core-in-1"
  dst: "Leg30Joint-out-0"
  weight: -0.297565117243
}
connection {
  src: "Core-in-5"
  dst: "Core-hidden-0"
  weight: 1.97833082195
}
connection {
  src: "Leg21Joint-out-0"
  dst: "augment1425"
  weight: 5.86460436595
}
connection {
  src: "augment1425"
  dst: "Leg11Joint-out-0"
  weight: -2.13844360209
}
connection {
  src: "Leg10Joint-out-0"
  dst: "Leg21Joint-out-0"
  weight: -0.0513184722671
}
connection {
  src: "Core-hidden-1"
  dst: "augment2667"
  weight: 13.7343135439
}
connection {
  src: "augment2667"
  dst: "Core-hidden-0"
  weight: 1.0
}
