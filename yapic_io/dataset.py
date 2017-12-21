import numpy as np
from numpy.random import choice, randint
randint_array = np.vectorize(randint)

import random
import collections

import yapic_io.utils as ut
from functools import lru_cache
import logging
import os
import yapic_io.transformations as trafo
import collections
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.INFO)
TrainingTile = collections.namedtuple('TrainingTile',
                                      ['pixels', 'channels', 'weights', 'labels', 'augmentation'])


class Dataset(object):
    '''
    provides connectors to pixel data source and
    (optionally) assigned weights for classifier training

    provides methods for getting image tiles and data
    augmentation for training

    pixel data is loaded lazily to allow images of arbitrary size
    pixel data is cached in memory for repeated requests
    '''

    def __init__(self, pixel_connector):
        self.pixel_connector = pixel_connector
        self.n_images = pixel_connector.image_count()
        self.label_counts = self.load_label_counts()

        # self.label_weights dict is complementary to self.label_counts
        self.label_weights = { label: 1 for label in self.label_counts.keys() }

        # max nr of trials to get a random training tile in polling mode
        self.max_pollings = 30

    def __repr__(self):
        return 'Dataset ({} images)'.format(self.n_images)

    @lru_cache(maxsize=1000)
    def image_dimensions(self, image_nr):
        '''
        returns dimensions of the dataset.
        dims is a 4-element-tuple:

        :param image_nr: index of image
        :returns (nr_channels, nr_zslices, nr_x, nr_y)
        '''
        return self.pixel_connector.image_dimensions(image_nr)

    def label_values(self):
        labels = list(self.label_counts.keys())
        labels.sort()
        return labels

    def random_training_tile(self,
                             size_zxy,
                             channels,
                             pixel_padding=(0, 0, 0),
                             equalized=False,
                             augment_params=None,
                             labels='all',
                             label_region=None):
        '''
        returns a randomly chosen training tile that contains labels
        of specific labelvalue specified in label_region.

        :param pos_zxy: tuple defining the upper left position of the tile in 3 dimensions zxy
        :type pos_zxy: tuple
        :param channels: list of pixel channels to be fetched
        :param pixel_padding: amount of padding to increase tile size in zxy
        :param equalized: If true, less frequent label_values are picked with same
                          probability as frequent label_values
        :param labels: list of labelvalues to be fetched
        :param label_region: labelvalue that must be present in the fetched tile region

        :returns: TrainingTile (pixels and corresponding labels)
        '''
        augment_params = augment_params or {}
        if labels == 'all':
            labels = self.label_values()

        if hasattr(self.pixel_connector, 'label_index_to_coordinate'):
            # fetch by label index
            return self._random_training_tile_by_coordinate(
                size_zxy,
                channels,
                labels,
                pixel_padding=pixel_padding,
                equalized=equalized,
                augment_params=augment_params,
                label_region=label_region)
        else:
            return self._random_training_tile_by_polling(
                size_zxy,
                channels,
                labels,
                pixel_padding=pixel_padding,
                equalized=equalized,
                augment_params=augment_params,
                label_region=label_region)

    def _random_pos_izxy(self, label_value, tile_size_zxy):
        '''
        get a random image and a random zxy position
        (for a tile of shape size_zxy) within this image.
        Images with more frequent labels of type label_value
        are more likely to be selected.
        '''
        # get random image by label probability
        # label probability per image
        label_prob = self._get_label_probs(label_value)
        img_nr = choice(len(label_prob), p=label_prob)

        # get random zxy position within selected image
        img_shape_zxy = self.image_dimensions(img_nr)[1:]
        img_maxpos_zxy = np.array(img_shape_zxy) - tile_size_zxy

        msg = 'Tile of size {} does not fit in image of size {}'.format(tile_size_zxy, img_shape_zxy)
        assert (img_maxpos_zxy > -1).all(), msg

        pos_zxy = randint_array(img_maxpos_zxy + 1)
        return img_nr, pos_zxy

    def _get_label_probs(self, label_value):
        '''
        get probabilities for labels per image
        if label_value is None, probabilities for
        the sum of all label values is returned.
        '''
        if label_value is None:
            # label count for all labelvalues
            lbl_count = sum(self.label_counts.values())
        else:
            lbl_count = self.label_counts[label_value]
        return lbl_count / lbl_count.sum()


    def _random_training_tile_by_polling(self,
                                         size_zxy,
                                         channels,
                                         labels,
                                         pixel_padding=(0, 0, 0),
                                         equalized=False,
                                         augment_params=None,
                                         label_region=None):
        ''''
        fetches a random training tile by repeated polling until
        the label specified in label_region is at least one time
        represented in the tile. The number if trials is set in
        self.max_pollings.
        If the nr of trials exceeds max_pollings, the last fetched
        tile is returned, although not containing the label.
        '''
        augment_params = augment_params or {}
        if label_region is None and equalized:
            label_region = self.random_label_value(equalized=equalized)

        for counter in range(self.max_pollings):
            img_nr, pos_zxy = self._random_pos_izxy(label_region, size_zxy)

            tile_data = self.training_tile(img_nr, pos_zxy, size_zxy,
                                           channels, labels,
                                           pixel_padding=pixel_padding,
                                           augment_params=augment_params)
            if label_region is None:
                # check if weights for any label are present
                are_weights_in_tile = tile_data.weights.any()
            else:
                # check if weights for specified label are present
                lblregion_index = np.where(np.array(tile_data.labels) == label_region)[0]

                weights_lblregion = tile_data.weights[lblregion_index]
                are_weights_in_tile = weights_lblregion.any()

            if are_weights_in_tile:
                msg = 'Needed {} trials to fetch random tile containing labelvalue {}'.format(counter, label_region or '<any>')
                logger.info(msg)
                return tile_data

        msg = 'Could not fetch random tile containing labelvalue {} within {} trials'
        logger.warning(msg.format(label_region, counter))

        # if no labelweights are present from any labelvalue
        if not tile_data.weights.any():
            logger.warning('training labelweighs do not contain any weights above 0 for any label')

        return tile_data

    def _random_training_tile_by_coordinate(self,
                                            size_zxy,
                                            channels,
                                            labels,
                                            pixel_padding=(0, 0, 0),
                                            equalized=False,
                                            augment_params=None,
                                            label_region=None):
        augment_params = augment_params or {}
        if label_region is None:
            # pick training tile where it is assured that weights for a specified label
            # are within the tile. the specified label is label_region
            label_region = self.random_label_value(equalized=equalized)

        total_count = self.label_counts[label_region].sum()
        coor = self.label_coordinate(label_region, randint(total_count))

        img_nr = coor[0]
        coor_zxy = coor[2:]
        shape_zxy = self.image_dimensions(img_nr)[1:]
        pos_zxy = np.array(ut.get_random_pos_for_coordinate(
            coor_zxy, size_zxy, shape_zxy))

        tile_data = self.training_tile(img_nr, pos_zxy, size_zxy,
                                       channels, labels, pixel_padding=pixel_padding,
                                       augment_params=augment_params)

        return tile_data

    def training_tile(self,
                      image_nr,
                      pos_zxy,
                      size_zxy,
                      channels,
                      labels,
                      pixel_padding=(0, 0, 0),
                      reflect=True,
                      augment_params=None):
        augment_params = augment_params or {}
        # 4d pixel tile with selected channels in 1st dimension
        pixel_tile = self.multichannel_pixel_tile(image_nr, pos_zxy, size_zxy, channels,
                                                  pixel_padding=pixel_padding,
                                                  augment_params=augment_params)

        # 4d label tile with selected labels in 1st dimension
        shape_zxy = self.image_dimensions(image_nr)[1:]
        label_tile = [ augment_tile(shape_zxy, pos_zxy, size_zxy,
                                    self._get_weights_tile,
                                    augment_params=augment_params,
                                    reflect=reflect,
                                    image_nr=image_nr,
                                    label_value=l)
                       for l in labels ]
        label_tile = np.array(label_tile)

        msg = 'pixel tile dim={} label tile dim={} labels={}'
        logger.debug(msg.format(pixel_tile.shape, label_tile.shape, len(labels)))

        return TrainingTile(pixel_tile, channels, label_tile, labels, augment_params)

    def multichannel_pixel_tile(self,
                                image_nr,
                                pos_zxy,
                                size_zxy,
                                channels,
                                pixel_padding=(0, 0, 0),
                                reflect=True,
                                augment_params=None):
        augment_params = augment_params or {}
        np.testing.assert_equal(len(pos_zxy), 3, 'Expected 3 dimensions (Z,X,Y)')
        np.testing.assert_equal(len(size_zxy), 3, 'Expected 3 dimensions (Z,X,Y)')

        image_shape_zxy = self.image_dimensions(image_nr)
        ut.assert_valid_image_subset(image_shape_zxy[1:], pos_zxy, size_zxy)

        pixel_padding = np.array(pixel_padding)
        size_padded = size_zxy + 2 * pixel_padding
        pos_padded = pos_zxy - pixel_padding

        tile = [ augment_tile(image_shape_zxy,
                              np.hstack([[c], pos_padded]),
                              np.hstack([[1], size_padded]),
                              self.pixel_connector.get_tile,
                              reflect=reflect,
                              augment_params=augment_params,
                              image_nr=image_nr)
                for c in channels]

        return np.vstack(tile)

    def _get_weights_tile(self, image_nr=None, pos=None, size=None, label_value=None):
        '''
        returns a 3d weight matrix tile for a certain label with dimensions zxy.
        '''
        assert label_value in self.label_values()

        boolmat = self.pixel_connector.label_tile(image_nr, pos, size, label_value)

        weight_mat = np.zeros_like(boolmat, float)
        weight_mat[boolmat] = self.label_weights[label_value]

        return weight_mat

    def equalize_label_weights(self):
        '''
        equalizes labels according to their amount.
        less frequent labels are weighted higher than more frequent labels
        '''
        weights = {
            l: np.nan_to_num(1.0 / img_counts.sum())
            for l, img_counts in self.label_counts.items()
        }

        self.label_weights = { l: c / sum(weights.values()) for l, c in weights.items() }


    def load_label_counts(self):
        '''
        returns the cout of each labelvalue for each image as dict

        label_counts = {
             label_value_1 : [nr_labels_image_0, nr_labels_image_1, nr_labels_image_2, ...],
             label_value_2 : [nr_labels_image_0, nr_labels_image_1, nr_labels_image_2, ...],
             label_value_2 : [nr_labels_image_0, nr_labels_image_1, nr_labels_image_2, ...],
             ...
        }
        '''
        logger.debug('Starting to load label counts...')

        label_counts = collections.defaultdict(lambda: np.zeros(self.n_images, dtype='int64'))
        for i in range(self.n_images):
            img_label_counts = self.pixel_connector.label_count_for_image(i) or {}

            for label_value in img_label_counts.keys():
                label_counts[label_value][i] = img_label_counts[label_value]

        logger.debug('label_counts: %i', label_counts)
        return dict(label_counts)


    def sync_label_counts(self, datset):
        '''
        Should be applied e.g. if two datasets were created from splitted
        conncetors( e.g. with tiff_connector.split(). Typical use case
        is syncing a training dataset and a validation dataset.

        >>> from yapic_io.dataset import Dataset
        >>> from yapic_io.tiff_connector import TiffConnector
        >>> from pprint import pprint
        >>>
        >>> pixel_image_dir = 'yapic_io/test_data/tiffconnector_1/im/*.tif'
        >>> label_image_dir = 'yapic_io/test_data/tiffconnector_1/labels/*.tif'
        >>> c = TiffConnector(pixel_image_dir, label_image_dir)
        >>> c1, c2 = c.split(1./3.)
        >>>
        >>> d = Dataset(c)
        >>> d1 = Dataset(c1)
        >>> d2 = Dataset(c2)
        >>>
        >>> pprint(d.label_counts) # full dataset has three labelvalues
        {1: array([4, 0, 0]), 2: array([ 3,  0, 11]), 3: array([3, 0, 3])}
        >>>
        >>> pprint(d1.label_counts) # d1 has also three labelvalues
        {1: array([4]), 2: array([3]), 3: array([3])}
        >>>
        >>> pprint(d2.label_counts) #d2 has only two labelvalues
        {2: array([ 0, 11]), 3: array([0, 3])}
        >>>
        >>>
        >>> d1.sync_label_counts(d2)
        >>> pprint(d1.label_counts)
        {1: array([4]), 2: array([3]), 3: array([3])}
        >>>
        >>> pprint(d2.label_counts) #labelvalue 1 added to d2 (with count 0)
        {1: array([0, 0]), 2: array([ 0, 11]), 3: array([0, 3])}

        '''
        lc1 = self.label_counts
        lc2 = datset.label_counts

        # missing label in each dataset
        missing_in_d1 = set(lc2.keys()) - set(lc1.keys())
        missing_in_d2 = set(lc1.keys()) - set(lc2.keys())

        for lbl in missing_in_d1:
            lc1[lbl] = np.zeros((self.n_images), dtype=np.int64)
        for lbl in missing_in_d2:
            lc2[lbl] = np.zeros((datset.n_images), dtype=np.int64)


    def label_coordinate(self, label_value, label_index):
        '''
        for each labelvalue there exist `index` labels in the dataset.
        returns the coordinate (image_nr, channel, z, x, y) of the nth label.
        '''
        counts = self.label_counts[label_value]
        counts_cs = counts.cumsum()
        total_count = counts_cs[-1]

        np.testing.assert_array_less(-1, label_index)
        np.testing.assert_array_less(label_index, total_count)

        image_nr = np.argmax(counts_cs > label_index)
        if image_nr > 0:
            label_index -= counts_cs[image_nr - 1]

        coor_czxy = self.pixel_connector.label_index_to_coordinate(image_nr, label_value, label_index)
        coor_iczxy = np.insert(coor_czxy, 0, image_nr)
        return coor_iczxy


    def random_label_value(self, equalized=False):
        '''
        returns a randomly chosen label value:

        :param equalized: If true, less frequent label_values are picked with same probability as frequent label_values
        :type equalized: bool
        '''
        if equalized:
            return random.choice(self.label_values())

        # probabilities for each labelvalue
        total_counts = [ counts.sum() for counts in self.label_counts.values() ]
        total_counts_norm = np.array(total_counts) / sum(total_counts)

        # pick a labelvalue according to the labelvalue probability
        return np.random.choice(self.label_values(), p=total_counts_norm)


def inner_tile_size(image_shape, pos, tile_shape):
    '''
    if a requested tile is out of bounds, this function calculates
    a transient tile position size and pos. The transient tile has to be padded in a
    later step to extend the edges for delivering the originally requested out of
    bounds tile. The padding sizes for this step are also delivered.
    size_out and pos_out that can be used in a second step with padding.
    pos_tile defines the position in the transient tile for cutting out the originally
    requested tile.

    :param image_shape: shape of full size original image
    :param pos: upper left position of tile in full size original image
    :param tile_shape: size of tile
    :returns pos_out, size_out, pos_tile, padding_sizes

    pos_out is the position inside the full size original image for the transient tile.
    (more explanation needed)
    '''
    padding_lower = np.maximum(0, -pos)
    padding_upper = np.maximum(0, pos - (image_shape - tile_shape))
    padding = np.vstack([padding_lower, padding_upper]).T

    pos_tile = np.maximum(0, pos + padding_upper - image_shape)
    pos_out = pos + padding_lower - pos_tile

    # WTF is going on here??
    size_inmat = tile_shape + np.minimum(0, pos)

    size_new_1 = np.maximum(padding_lower, size_inmat)
    size_new_2 = np.minimum(tile_shape, image_shape - pos_out)
    size_out = np.minimum(size_new_1, size_new_2)

    return tuple(pos_out), tuple(size_out), tuple(pos_tile), tuple(padding)


def augment_tile(img_shape,
                 pos,
                 tile_shape,
                 get_tile_func,
                 augment_params=None,
                 reflect=True,
                 **kwargs):
    '''
    fetch tile and augment it
    if rotation and shear is activated, a 3 times larger tile
    is fetched and the final tile is cut out from that after
    rotation/shear.
    '''
    augment_params = augment_params or {}
    rotation_angle = augment_params.get('rotation_angle', 0)
    shear_angle = augment_params.get('shear_angle', 0)

    pos = np.array(pos)
    orig_tile_shape = np.array(tile_shape)
    tile_shape = np.array(tile_shape)

    augment_fast = (tile_shape[-2:] > 1).any()
    augment_slow = augment_fast and (rotation_angle > 0 or shear_angle > 0)

    if augment_slow:
        pos -= tile_shape
        tile_shape *= 3

    res = inner_tile_size(img_shape, pos, tile_shape)
    pos_transient, size_transient, pos_inside_transient, pad_size = res

    tile = get_tile_func(pos=pos_transient, size=size_transient, **kwargs)

    assert np.all(pad_size ==0) or reflect, 'requested tile out of bounds'
    tile = np.pad(tile, pad_size, mode='symmetric')
    mesh = ut.get_tile_meshgrid(tile.shape, pos_inside_transient, tile_shape)
    tile = tile[mesh]

    if augment_fast:
        # if the requested tile is only of size 1 in x and y,
        # augmentation can be omitted, since rotation and flipping always
        # occurs around the center axis.
        rot90 = augment_params.get('rot90', 0)
        flipud = augment_params.get('flipud', False)
        fliplr = augment_params.get('fliplr', False)

        tile = trafo.flip_image_2d_stack(tile, fliplr=fliplr,
                                         flipud=flipud, rot90=rot90)

    if augment_slow:
        tile = trafo.warp_image_2d_stack(tile, rotation_angle, shear_angle)
        mesh = ut.get_tile_meshgrid(tile.shape, orig_tile_shape, orig_tile_shape)
        tile = tile[mesh]

    return tile
