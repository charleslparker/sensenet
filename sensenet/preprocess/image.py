import sensenet.importers
tf = sensenet.importers.import_tensorflow()

from sensenet.constants import IMAGE_STANDARDIZERS
from sensenet.pretrained import complete_image_network
from sensenet.layers.utils import constant, propagate
from sensenet.layers.construct import layer_sequence

class ImageReader(tf.keras.layers.Layer):
    def __init__(self, network, extras):
        super(ImageReader, self).__init__()

        ishape = network['metadata']['input_image_shape']

        self._input_shape = [None, ishape[1], ishape[0], ishape[2]]
        self._path_prefix = extras.get('path_prefix', None)
        self._input_format = extras.get('input_image_format', 'file')

    def build(self, input_shape):
        dims = tf.constant(self._input_shape[1:3], tf.int32)
        nchannels = self._input_shape[-1]

        def read_image(path_or_bytes):
            if self._input_format == 'file':
                path = path_or_bytes

                if self._path_prefix:
                    path = tf.strings.join([self._path_prefix, path])

                img_bytes = tf.io.read_file(path)
            else:
                img_bytes = path_or_bytes

            # Note that, spectacularly weirdly, this method will also
            # work for pngs and gifs.  Even wierder, We can't use
            # decode_image here because the tensor that comes out
            # doesn't have a shape!
            raw_image = tf.io.decode_jpeg(img_bytes,
                                          dct_method='INTEGER_ACCURATE',
                                          channels=nchannels)

            return tf.image.resize(raw_image, dims, method='nearest')

        self._read = read_image

    def call(self, inputs):
        images = tf.map_fn(self._read, inputs, back_prop=False, dtype=tf.uint8)
        return tf.cast(images, tf.float32)

class ImageLoader(tf.keras.layers.Layer):
    def __init__(self, network):
        super(ImageLoader, self).__init__()

        metadata = network['metadata']
        method = metadata['loading_method']
        mimg = metadata['mean_image']
        mean, std = IMAGE_STANDARDIZERS[method]

        self._reverse = method == 'channelwise_centering'
        self._mean = constant(mean) if mean != 0 else None
        self._stdev = constant(std) if std != 1 else None
        self._mean_image = constant(mimg) if mimg is not None else None

    def call(self, inputs):
        images = inputs

        if self._reverse:
            images = tf.reverse(images, axis=[-1])

        if self._mean_image is not None:
            images = images - self._mean_image

        if self._mean is not None:
            images = images - self._mean

        if self._stdev is not None:
            images = images / self._stdev

        return images

class ImagePreprocessor(tf.keras.layers.Layer):
    def __init__(self, image_network, extras):
        super(ImagePreprocessor, self).__init__()

        network = complete_image_network(image_network)

        self._reader = ImageReader(network, extras)
        self._loader = ImageLoader(network)
        self._image_layers = layer_sequence(network)

    def call(self, inputs):
        raw_images = self._reader(inputs)
        images = self._loader(raw_images)

        return propagate(self._image_layers, images)