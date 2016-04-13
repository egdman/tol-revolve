import os
import sys
import yaml
import graphviz as gv


from argparse import ArgumentParser

parser = ArgumentParser("draw_nn.py")

parser.add_argument('-i', '--input_path', metavar='INPUT', type=str, help="Path to a genotype YAML file")
parser.add_argument('-o', '--output_path', metavar='OUTPUT', type=str, help="Path to a graph drawing")


def main():
    args = parser.parse_args()


    graph = gv.Digraph(
        format='png',
        engine='fdp',
    )

    with open(args.input_path, 'r') as in_file:
        yaml_nn = in_file.read()

    nn = yaml.load(yaml_nn)
    neurons = nn['neurons']
    connections = nn['connections']
    inputs = []
    outputs = []
    hidden = []
    for neuron in neurons:
        if neuron['layer'] == 'input':
            inputs.append(neuron)
        elif neuron['layer'] == 'output':
            outputs.append(neuron)
        else:
            hidden.append(neuron)

    num_inputs = len(inputs)
    num_outputs = len(outputs)

    canvas_width = 10
    margin = 0.5

    in_spacing = float(canvas_width) / float(num_inputs)
    out_spacing = float(canvas_width) / float(num_outputs)

    inputs_added = 0
    outputs_added = 0


    for n in inputs:
        if n['enabled']:
            coord_x = margin
            coord_y = margin + in_spacing * inputs_added
            inputs_added += 1
            pos = "{0},{1}!".format(coord_x, coord_y)
            label = "{0}, {1}".format(n['id'], n['hist_mark'])
            graph.node(name=n['id'], label=label, _attributes={"pos" : pos, "shape": "box"})

    for n in outputs:
        if n['enabled']:
            coord_x = margin + canvas_width
            coord_y = margin + out_spacing * outputs_added
            outputs_added += 1
            pos = "{0},{1}!".format(coord_x, coord_y)
            label = "{0}, {1}".format(n['id'], n['hist_mark'])
            graph.node(name=n['id'], label=label, _attributes={"pos" : pos, "shape": "box"})

    for n in hidden:
        if n['enabled']:
            label = "{0}, {1}".format(n['type'], n['hist_mark'])
            graph.node(name=n['id'], label=label)

    for c in connections:
        if c['enabled']:
            linestyle = 'solid'
            mark_from = c['from']
            mark_to = c['to']
            n_from = filter(lambda neuron: neuron['hist_mark'] == mark_from, neurons)[0]
            n_to = filter(lambda neuron: neuron['hist_mark'] == mark_to, neurons)[0]
            graph.edge(n_from['id'], n_to['id'], _attributes={'style': linestyle})

    graph.render(filename=args.output_path)


if __name__ == '__main__':
    main()
