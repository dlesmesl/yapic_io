import logging
import os
import glob
import itertools
import collections
from functools import lru_cache
import yapic_io.utils as ut
import numpy as np
import itertools
import warnings
from itertools import zip_longest

import yapic_io.image_importers as ip
from yapic_io.utils import get_tile_meshgrid, add_to_filename, find_best_matching_pairs
from yapic_io.connector import Connector
from pprint import pprint
logger = logging.getLogger(os.path.basename(__file__))

FilePair = collections.namedtuple('FilePair', ['img', 'lbl'])


class TiffConnector(Connector):
    '''
    implementation of Connector for normal sized tiff images (up to 4 dimensions)
    and corresponding label masks (up to 4 dimensions) in tiff format.

    Initiate a new TiffConnector as follows:

    >>> from yapic_io.tiff_connector import TiffConnector
    >>> pixel_image_dir = 'yapic_io/test_data/tiffconnector_1/im/*.tif'
    >>> label_image_dir = 'yapic_io/test_data/tiffconnector_1/labels/*.tif'
    >>> t = TiffConnector(pixel_image_dir, label_image_dir)
    >>> print(t)
    <TiffConnector(imgpath=yapic_io/test_data/tiffconnector_1/im, lblpath=yapic_io/test_data/tiffconnector_1/labels)>
    '''
    def __init__(self, img_filepath, label_filepath,
            savepath=None,
            zstack=True,
            multichannel_pixel_image=None,
            multichannel_label_image=None):
        '''
        :param img_filepath: path to source pixel images (use wildcards for filtering)
                             or a list of filenames
        :param label_filepath: path to label images (use wildcards for filtering)
                               or a list of filenames
        :param savepath: path for output probability images
        :param multichannel_pixel_image: set True if pixel images have multiple channels
        :type multichannel_pixel_image: bool
        :param multichannel_label_image: set True if label images have multiple channels
        :type multichannel_label_image: bool
        :param zstack: set True if label- and pixel images are zstacks
        :type zstack: bool

        Label images and pixel images have to be equal in zxy dimensions, but can differ
        in nr of channels.

        Labels can be read from multichannel images. This is needed for networks
        with multilee output layers. Each channel is assigned one output layer.
        Different labels from different channels can overlap (can share identical
        xyz positions).

        Multichannel_pixel_image, multichannel_pixel_image and zstack
        can be set to None. In this case the importer tries to map
        dimensions automatically. This does not always work, esp. in case
        of 3 dimensional images.


        Examples:

        - If zstack is set to False and multichannel_pixel_image is set to None,
          the importer will assign the thrid dimensions (in case of 3 dimensional images)
          to channels, i.e. interprets the image as multichannel, single z image.

        - If zstack is set to None and multichannel_pixel_image is set to None,
          the importer will assign all dims correctly in case of 4 dimensional images
          and in case of 2 dimensional images (single z, singechannel). In case of 3
          dimensional images, it throws an error, because it is not clear if the thrid
          dimension is z or channel (RGB images will still be mapped correctly)
        '''
        self.filenames = None # list of FilePairs: [(imgfile_1.tif, labelfile_1.tif), (imgfile_2.tif, labelfile_2.tif), ...]
        self.labelvalue_mapping = None # list of dicts of original and assigned labelvalues
        self.savepath = savepath # path for probability maps
        self.zstack = zstack
        self.multichannel_pixel_image = multichannel_pixel_image
        self.multichannel_label_image = multichannel_label_image

        if type(img_filepath) == str:
            assert type(label_filepath) == str

            img_filepath = os.path.normpath(os.path.expanduser(img_filepath))
            lbl_filepath = os.path.normpath(os.path.expanduser(label_filepath))

            if os.path.isdir(img_filepath):
                img_filepath = os.path.join(img_filepath, '*.tif')
            if os.path.isdir(lbl_filepath):
                lbl_filepath = os.path.join(lbl_filepath, '*.tif')

            self.img_path, img_filemask = os.path.split(img_filepath)
            self.label_path, label_filemask = os.path.split(lbl_filepath)

            img_filenames = [os.path.basename(fname) for fname in sorted(glob.glob(img_filepath))]
            lbl_filenames = [os.path.basename(fname) for fname in sorted(glob.glob(lbl_filepath))]

            pairs = find_best_matching_pairs(img_filenames, lbl_filenames)
            self.filenames = [FilePair(img, lbl) for img, lbl in pairs]
        else:
            img_filenames = img_filepath
            lbl_filenames = label_filepath

            if len(img_filenames) > 0:
                self.img_path = os.path.dirname(img_filenames[0])
                img_filenames = [os.path.basename(fname) if fname is not None else None for fname in img_filenames]
            else:
                self.img_path = None

            filtered_labels = [fname for fname in lbl_filenames if fname is not None]
            if len(filtered_labels) > 0:
                self.label_path = os.path.dirname(filtered_labels[0])
                lbl_filenames = [os.path.basename(fname) if fname is not None else None for fname in lbl_filenames]
            else:
                self.label_path = None

            self.filenames = [FilePair(img, lbl) for img, lbl in zip(img_filenames, lbl_filenames)]

        assert img_filenames is not None
        assert lbl_filenames is not None

        logger.info('{} pixel image files detected.'.format(len(img_filenames)))
        logger.debug('Pixel image files:')
        logger.debug(img_filenames)

        if len(img_filenames) != len(lbl_filenames):
            msg = 'Number of image files ({}) and label files ({}) differ!'
            logger.warning(msg.format(len(img_filenames), len(lbl_filenames)))

        logger.debug('Pixel and label files are assigned as follows:')
        logger.debug('\n'.join('{p.img} <-> {p.lbl}'.format(p=pair) for pair in self.filenames))

        self.check_label_matrix_dimensions()

        original_labels = self.original_label_values_for_all_images()
        self.labelvalue_mapping = self.calc_label_values_mapping(original_labels)


    def __repr__(self):
        return '<TiffConnector(imgpath={}, lblpath={})>'.format(self.img_path, self.label_path)


    def filter_labeled(self):
        '''
        Returns a new TiffConnector containing only images that have labels
        '''
        img_fnames = [os.path.join(self.img_path, img) for img, lbl in self.filenames
                      if lbl is not None]

        lbl_fnames = [os.path.join(self.label_path, lbl)
                      for img, lbl in self.filenames
                      if lbl is not None]

        return TiffConnector(img_fnames, lbl_fnames,
                             savepath=self.savepath,
                             multichannel_pixel_image=self.multichannel_pixel_image,
                             multichannel_label_image=self.multichannel_label_image,
                             zstack=self.zstack)


    def split(self, fraction, random_seed=42):
        '''
        Split the images pseudo-randomly into two subsets (both TiffConnectors).
        The first of size `(1-fraction)*N_images`, the other of size `fraction*N_images`
        '''
        N = len(self.filenames)

        state = np.random.get_state()
        np.random.seed(random_seed)
        mask = np.random.choice([True, False], size=N, p=[1-fraction, fraction])
        np.random.set_state(state)

        img_fnames1 = [os.path.join(self.img_path, img)
                       for img, lbl in itertools.compress(self.filenames, mask)]
        lbl_fnames1 = [os.path.join(self.label_path, lbl) if lbl is not None else None
                       for img, lbl in itertools.compress(self.filenames, mask)]

        img_fnames2 = [os.path.join(self.img_path, img)
                       for img, lbl in itertools.compress(self.filenames, ~mask)]
        lbl_fnames2 = [os.path.join(self.label_path, lbl) if lbl is not None else None
                       for img, lbl in itertools.compress(self.filenames, ~mask)]

        if len(img_fnames1) == 0:
            warnings.warn('TiffConnector.split({}): First connector is empty!'.format(fraction))
        if len(img_fnames2) == 0:
            warnings.warn('TiffConnector.split({}): Second connector is empty!'.format(fraction))

        conn1 = TiffConnector(img_fnames1, lbl_fnames1,
                              savepath=self.savepath,
                              multichannel_pixel_image=self.multichannel_pixel_image,
                              multichannel_label_image=self.multichannel_label_image,
                              zstack=self.zstack)
        conn2 = TiffConnector(img_fnames2, lbl_fnames2,
                              savepath=self.savepath,
                              multichannel_pixel_image=self.multichannel_pixel_image,
                              multichannel_label_image=self.multichannel_label_image,
                              zstack=self.zstack)

        # ensures that both resulting tiff_connectors have the same
        # labelvalue mapping (issue #1)
        conn1.labelvalue_mapping = self.labelvalue_mapping
        conn2.labelvalue_mapping = self.labelvalue_mapping

        #np.random.seed(None)
        return conn1, conn2


    def image_count(self):
        return len(self.filenames)


    def put_tile(self, pixels, pos_zxy, image_nr, label_value):
        np.testing.assert_equal(len(pos_zxy), 3, '{} must have length of 3'.format(pos_zxy))
        np.testing.assert_equal(len(pixels.shape), 3, '{} must have shape of 3'.format(pixels.shape))

        path = self.init_probmap_image(image_nr, label_value)
        return ip.add_vals_to_tiff_image(path, pos_zxy, pixels)


    def init_probmap_image(self, image_nr, label_value, overwrite=False):
        assert self.savepath is not None
        image_filename = self.filenames[image_nr].img

        path, ext = os.path.splitext(image_filename)
        probmap_filename = '{}_class_{}{}'.format(path, label_value, ext)
        out_path = os.path.join(self.savepath, probmap_filename)

        if overwrite or not os.path.exists(out_path):
            logger.debug('initializing a new probmap image: %s', out_path)
            _, Z, X, Y = self.image_dimensions(image_nr)
            ip.init_empty_tiff_image(out_path, X, Y, z_size=Z)

        return out_path


    @lru_cache(maxsize=5000)
    def get_tile(self, image_nr, pos, size):
        im = self.load_image(image_nr)
        mesh = get_tile_meshgrid(im.shape, pos, size)

        return im[mesh]


    def image_dimensions(self, image_nr):
        '''
        returns dimensions of the dataset.
        dims is a 4-element-tuple:

        :param image_nr: index of image
        :returns (nr_channels, nr_zslices, nr_x, nr_y)
        '''
        path = os.path.join(self.img_path, self.filenames[image_nr].img)
        return ip.get_tiff_image_dimensions(path, zstack=self.zstack,
                                            multichannel=self.multichannel_pixel_image)


    def label_matrix_dimensions(self, image_nr):
        '''
        returns dimensions of the label image.
        dims is a 4-element-tuple:

        :param image_nr: index of image
        :returns (nr_channels, nr_zslices, nr_x, nr_y)
        '''
        if self.filenames[image_nr].lbl is None:
            return None

        path = os.path.join(self.label_path, self.filenames[image_nr].lbl)
        return ip.get_tiff_image_dimensions(path, zstack=self.zstack,
                                            multichannel=self.multichannel_label_image)


    def check_label_matrix_dimensions(self):
        '''
        check if label matrix dimensions fit to image dimensions, i.e.
        everything identical except nr of channels (label mat always 1)
        '''
        N_channels = None

        for i, (img_fname, lbl_fname) in enumerate(self.filenames):
            img_dim = self.image_dimensions(i)
            lbl_dim = self.label_matrix_dimensions(i)

            msg = 'Dimensions for image #{}: img.shape={}, lbl.shape={}'
            logger.debug(msg.format(i, img_dim, lbl_dim))

            if lbl_dim is None:
                continue

            _,  *img_dim = img_dim
            ch, *lbl_dim = lbl_dim

            if N_channels is None:
                N_channels = ch

            np.testing.assert_equal(N_channels, ch, 'Label channels inconsistent for {}'.format(lbl_fname))
            np.testing.assert_array_equal(lbl_dim, img_dim, 'Invalid image dims for {} and {}'.format(img_fname, lbl_fname))


    @lru_cache(maxsize = 20)
    def load_image(self, image_nr):
        path = os.path.join(self.img_path, self.filenames[image_nr].img)
        return ip.import_tiff_image(path)


    def label_tile(self, image_nr, pos_zxy, size_zxy, label_value):
        '''
        returns a 3d zxy boolean matrix where positions of the reuqested label
        are indicated with True. only mapped labelvalues can be requested.
        '''
        labelmat = self.load_label_matrix(image_nr) # matrix with labelvalues
        boolmat_4d = (labelmat == label_value)

        boolmat_3d = boolmat_4d.any(axis=0) # reduction to zxy dimension
        # comment: mapped labelvalues are unique for a channel, as they
        # are generated with map_label_values(). This means,
        # a mapped labelvalue is only present in one specific channel.
        # This means: there could be not more than one truthy value along the
        # channel dimension in boolmat_4d. this is not doublechecked here.

        mesh = get_tile_meshgrid(boolmat_3d.shape, pos_zxy, size_zxy)
        return boolmat_3d[mesh]


    @lru_cache(maxsize = 20)
    def load_label_matrix(self, image_nr, original_labelvalues=False):
        '''
        returns a 4d labelmatrix with dimensions czxy.
        the albelmatrix consists of zeros (no label) or the respective
        label value.

        if original_labelvalues is False, the mapped label values are returned,
        otherwise the original labelvalues.
        '''
        label_filename = self.filenames[image_nr].lbl

        if label_filename is None:
            logger.warning('no label matrix file found for image file %s', str(image_nr))
            return None

        path = os.path.join(self.label_path, label_filename)
        logger.debug('Trying to load labelmat %s', path)

        label_image = ip.import_tiff_image(path, zstack=self.zstack,
                                           multichannel=self.multichannel_label_image)

        if not original_labelvalues:
            label_image = ut.assign_slice_by_slice(self.labelvalue_mapping, label_image)

        return label_image


    @staticmethod
    def calc_label_values_mapping(original_labels):
        '''
        assign unique labelvalues to original labelvalues.
        for multichannel label images it might happen, that identical
        labels occur in different channels.
        to avoid conflicts, original labelvalues are mapped to unique values
        in ascending order 1, 2, 3, 4...

        This is defined in self.labelvalue_mapping:

        [{orig_label1: 1, orig_label2: 2}, {orig_label1: 3, orig_label2: 4}, ...]

        Each element of the list correponds to one label channel.
        Keys are the original labels, values are the assigned labels that
        will be seen by the Dataset object.
        '''
        new_labels = itertools.count(1)

        label_mappings = [
            { l: next(new_labels) for l in sorted(labels_per_channel) }
            for labels_per_channel in original_labels
        ]

        logger.debug('Label values are mapped to ascending values:')
        logger.debug(label_mappings)
        return label_mappings


    @lru_cache(maxsize = 1)
    def original_label_values_for_all_images(self):
        '''
        returns a list of sets. each set corresponds to 1 label channel.
        each set contains the label values of that channel.
        E.g. `[{91, 109, 150}, {90, 100}]` for two label channels
        '''
        labels_per_channel = []

        for image_nr in range(self.image_count()):
            mat = self.load_label_matrix(image_nr, original_labelvalues=True)
            if mat is None:
                continue

            labels = [ np.unique(mat[ch]) for ch in range(mat.shape[0]) ]
            labels = [ set(labels) - {0} for labels in labels ]

            labels_per_channel = [ l1.union(l2) for l1, l2
                                   in zip_longest(labels_per_channel, labels, fillvalue=set()) ]

        return labels_per_channel


    @lru_cache(maxsize = 1500)
    def label_count_for_image(self, image_nr):
        '''
        returns for each label value the number of labels for this image
        '''
        mat = self.load_label_matrix(image_nr)
        if mat is None:
            return None

        labels = np.unique(mat)

        label_count = { l: np.count_nonzero(mat==l) for l in labels if l > 0 }
        return label_count
