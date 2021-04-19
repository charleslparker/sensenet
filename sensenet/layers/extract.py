import pprint

def add(config, layer):
    return {'type': 'add'}

def activation(config, layer):
    return {
        'type': 'activation',
        'activation_function': layer.activation.__name__
    }

def batchnorm(config, layer):
    gamma, beta, mean, variance = layer.get_weights()

    return {
        'type': 'batch_normalization',
        'epsilon': config['epsilon'],
        'gamma': gamma.tolist(),
        'beta': beta.tolist(),
        'mean': mean.tolist(),
        'variance': variance.tolist()
    }

def concat(config, layer):
    return {'type': 'concatenate'}

def conv_2d(config, layer):
    if config['use_bias']:
        kernel, bias = layer.get_weights()
    else:
        kernel = layer.get_weights()[0]
        bias = None

    return {
        'type': 'convolution_2d',
        'kernel': kernel.tolist(),
        'bias': bias.tolist() if bias is not None else None,
        'activation_function': config['activation'],
        'padding': config['padding'],
        'strides': config['strides']
    }

def dense(config, layer):
    if config['use_bias']:
        weights, offset = layer.get_weights()
    else:
        weights = layer.get_weights()[0]
        offset = None

    return {
        'type': 'dense',
        'weights': weights.tolist(),
        'offset': offset.tolist() if offset is not None else None,
        'activation_function': config['activation']
    }

def depthwise_conv_2d(config, layer):
    if config['use_bias']:
        kernel, bias = layer.get_weights()
    else:
        kernel = layer.get_weights()[0]
        bias = None

    return {
        'type': 'depthwise_convolution_2d',
        'kernel': kernel.tolist(),
        'bias': bias.tolist() if bias is not None else None,
        'activation_function': config['activation'],
        'padding': config['padding'],
        'strides': config['strides'],
        'depth_multiplier': config['depth_multiplier']
    }

def global_max_pool(config, layer):
    return {'type': 'global_max_pool_2d'}

def global_avg_pool(config, layer):
    return {'type': 'global_average_pool_2d'}

def lamda(config, layer):
    fname = layer.function.__name__

    if fname.startswith('split_'):
        pieces = fname.split('_')
        ith = int(pieces[1])
        nsplits = int(pieces[3])

        return {
            'type': 'split_channels',
            'number_of_splits': nsplits,
            'group_index': ith
        }
    else:
        raise ValueError('Cannot serialize lambda with function %s' % fname)

def max_pool(config, layer):
    return {
        'type': 'max_pool_2d',
        'padding': config['padding'],
        'strides': config['strides'],
        'pool_size': config['pool_size']
    }

def separable_conv_2d(config, layer):
    if config['use_bias']:
        depth_kernel, point_kernel, bias = layer.get_weights()
    else:
        depth_kernel, point_kernel = layer.get_weights()[:2]
        bias = None

    return {
        'type': 'separable_convolution_2d',
        'depth_kernel': depth_kernel.tolist(),
        'point_kernel': point_kernel.tolist(),
        'bias': bias.tolist() if bias is not None else None,
        'activation_function': config['activation'],
        'padding': config['padding'],
        'strides': config['strides'],
        'depth_multiplier': config['depth_multiplier']
    }

def upsample(config, layer):
    return {
        'type': 'upsampling_2d',
        'method': 'bilinear',
        'size': [2, 2]
    }

def zero_pad(config, layer):
    return {'type': 'padding_2d', 'padding': config['padding']}

LAYER_EXTRACTORS = {
    'Activation': activation,
    'Add': add,
    'BatchNormalization': batchnorm,
    'Concatenate': concat,
    'Conv2D': conv_2d,
    'Dense': dense,
    'DepthwiseConv2D': depthwise_conv_2d,
    'GlobalAveragePooling2D': global_avg_pool,
    'GlobalMaxPooling2D': global_max_pool,
    'Lambda': lamda,
    'MaxPooling2D': max_pool,
    'SeparableConv2D': separable_conv_2d,
    'UpSampling2D': upsample,
    'ZeroPadding2D': zero_pad
}

def extract_one(model, config):
    layer = model.get_layer(config['name'])

    try:
        processor = LAYER_EXTRACTORS[config['class_name']]
    except KeyError:
        pprint.pprint(config)
        raise ValueError('No processor for type %s' % config['name'])

    new_layer = processor(config['config'], layer)
    new_layer['name'] = config['name']
    new_layer['input_names'] = [n[0] for n in config['inbound_nodes'][0]]

    return new_layer

def index_in_model(model, ltype, nth):
    layers = model.get_config()['layers']
    matching = []

    for i, layer in enumerate(layers):
        if layer['class_name'] == ltype:
            matching.append(i)

    if not matching:
        raise ValueError('%s not found in model' % ltype)
    else:
        return matching[nth]

def name_index(layers, name):
    for i, layer in enumerate(layers):
        if layer['name'] == name:
            return i

    raise ValueError('%s not found in layer stack' % name)

def input_stack_indices(layer_map, layer_name):
    layer_indices = [layer_map[layer_name]['index']]

    if layer_map[layer_name]['inbound_nodes']:
        for in_layer in layer_map[layer_name]['inbound_nodes'][0]:
            layer_indices.extend(input_stack_indices(layer_map, in_layer[0]))

    return sorted(set(layer_indices))