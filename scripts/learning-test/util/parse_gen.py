
brain_file_path = 'gen_49_genotypes.log'
brain_num = 0

with open(brain_file_path, 'r') as brain_file:
    yaml_string = ''
    for line in brain_file:
        if 'velocity' in line:
            if yaml_string != '':
                with open("brain_{0}.yaml".format(brain_num), 'w') as out_file:
                    out_file.write(yaml_string)
                brain_num += 1
                yaml_string = ''
            continue
        yaml_string += line

    with open("brain_{0}.yaml".format(brain_num), 'w') as out_file:
        out_file.write(yaml_string)