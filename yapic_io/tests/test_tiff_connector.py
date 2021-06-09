import itertools
from unittest import TestCase
import os
import numpy as np
from numpy.testing import assert_array_equal
from yapic_io.tiff_connector import TiffConnector
import yapic_io.tiff_connector as tc
import logging
import tempfile
from pathlib import Path
logger = logging.getLogger(os.path.basename(__file__))

base_path = os.path.dirname(__file__)


class TestTiffConnector(TestCase):

    def test__handle_img_filenames(self):

        folder_val = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/')
        folder_val = Path(os.path.normpath(os.path.expanduser(folder_val)))

        filenames_val = ['6width4height3slices_rgb.tif',
                         '40width26height3slices_rgb.tif',
                         '40width26height6slices_rgb.tif']

        # str with wildcard
        img_path = os.path.normpath(os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif'))
        folder, names = tc._handle_img_filenames(img_path)
        self.assertEqual(folder, folder_val)
        self.assertEqual(set(filenames_val), set(names))

        # str without wildcard
        img_path = os.path.normpath(os.path.join(
            base_path, '../test_data/tiffconnector_1/im'))
        folder, names = tc._handle_img_filenames(img_path)
        self.assertEqual(folder, folder_val)
        self.assertEqual(set(filenames_val), set(names))

        # list of filepaths
        filenames = \
            [os.path.join(str(folder_val), '6width4height3slices_rgb.tif'),
             os.path.join(str(folder_val), '40width26height3slices_rgb.tif'),
             os.path.join(str(folder_val), '40width26height6slices_rgb.tif')]

        folder, names = tc._handle_img_filenames(filenames)
        self.assertEqual(folder, folder_val)
        self.assertEqual(set(filenames_val), set(names))

        # list of filepaths with None
        filenames = \
            [os.path.join(str(folder_val), '6width4height3slices_rgb.tif'),
             os.path.join(str(folder_val), '40width26height3slices_rgb.tif'),
             None,
             os.path.join(str(folder_val), '40width26height6slices_rgb.tif')]
        filenames_val = ['6width4height3slices_rgb.tif',
                         '40width26height3slices_rgb.tif',
                         None,
                         '40width26height6slices_rgb.tif']

        print(filenames)
        folder, names = tc._handle_img_filenames(filenames)
        self.assertEqual(folder, folder_val)
        self.assertEqual(set(filenames_val), set(names))

    def test_load_filenames(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        c = TiffConnector(img_path, 'path/to/nowhere/')

        img_filenames = [Path('6width4height3slices_rgb.tif'),
                         Path('40width26height3slices_rgb.tif'),
                         Path('40width26height6slices_rgb.tif')]

        fnames = [e[0] for e in c.filenames]
        self.assertEqual(set(img_filenames), set(fnames))

    def test_load_filenames_from_same_path(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/img*.tif')
        lbl_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/lbl*.tif')
        c = TiffConnector(img_path, lbl_path)

        expected_names = \
            [(Path('img_40width26height3slices_rgb.tif'),
              Path('lbl_40width26height3slices_rgb.tif')),
             (Path('img_40width26height6slices_rgb.tif'),
              None),
             (Path('img_6width4height3slices_rgb.tif'),
              Path('lbl_6width4height3slices_rgb.tif'))]

        self.assertEqual(c.filenames, expected_names)

    def test_filter_labeled(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/img*.tif')
        lbl_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/lbl*.tif')
        c = TiffConnector(img_path, lbl_path).filter_labeled()

        expected_names = \
            [(Path('img_40width26height3slices_rgb.tif'),
              Path('lbl_40width26height3slices_rgb.tif')),
             (Path('img_6width4height3slices_rgb.tif'),
              Path('lbl_6width4height3slices_rgb.tif'))]

        self.assertEqual(set(c.filenames), set(expected_names))

    def test_split(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/img*.tif')
        lbl_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/lbl*.tif')
        c = TiffConnector(img_path, lbl_path)
        c1, c2 = c.split(0.5)

        expected_names1 = [(Path('img_40width26height3slices_rgb.tif'),
                            Path('lbl_40width26height3slices_rgb.tif'))]
        expected_names2 = [(Path('img_40width26height6slices_rgb.tif'), None),
                           (Path('img_6width4height3slices_rgb.tif'),
                            Path('lbl_6width4height3slices_rgb.tif'))]

        self.assertEqual(set(c1.filenames), set(expected_names1))
        self.assertEqual(set(c2.filenames), set(expected_names2))

        # test for issue #1
        self.assertEqual(c1.labelvalue_mapping, c.labelvalue_mapping)
        self.assertEqual(c2.labelvalue_mapping, c.labelvalue_mapping)

    def test_load_filenames_emptyfolder(self):
        img_path = os.path.join(base_path, '../test_data/empty_folder/')

        with self.assertRaises(AssertionError):
            TiffConnector(img_path, 'path/to/nowhere/')

    def test_image_dimensions(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/img*.tif')
        lbl_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/lbl*.tif')
        c = TiffConnector(img_path, lbl_path)

        with self.assertRaises(IndexError):
            c.image_dimensions(4)

        np.testing.assert_array_equal(c.image_dimensions(0), (3, 3, 40, 26))
        np.testing.assert_array_equal(c.image_dimensions(1), (3, 6, 40, 26))
        np.testing.assert_array_equal(c.image_dimensions(2), (3, 3, 6, 4))

    def test_image_dimensions_multichannel(self):

        img_path = os.path.join(
            base_path,
            '../test_data/tif_images/1000width_992height_4channels_16bit.tif')
        c = TiffConnector(img_path, 'some/path')
        assert_array_equal(c.image_dimensions(0), [4, 1, 1000, 992])

        img_path = os.path.join(
            base_path,
            ('../test_data/tif_images/'
             '1000width_992height_4channels_16bit_hyperstack.tif'))
        c = TiffConnector(img_path, 'some/path')
        assert_array_equal(c.image_dimensions(0), [4, 1, 1000, 992])

    def test_get_tile(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/together/img*.tif')
        c = TiffConnector(img_path, 'path/to/nowhere/')

        image_nr = 0
        pos = (0, 0, 0, 0)
        size = (1, 1, 1, 2)
        tile = c.get_tile(image_nr=image_nr, pos=pos, size=size)
        val = np.empty(shape=size)
        val[0, 0, 0, 0] = 151
        val[0, 0, 0, 1] = 151
        val = val.astype(int)
        print(val)
        print(tile)
        np.testing.assert_array_equal(tile, val)

    def test_get_tile2(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/c2z2y2x2.tif')
        conn = TiffConnector(img_path, 'path/to/nowhere/')

        image_nr = 0
        pos = (0, 0, 0, 0)
        size = (2, 2, 2, 2)
        tile = conn.get_tile(image_nr=image_nr, pos=pos, size=size)
        expected = [[[[c * 2 ** 3 + z * 2 ** 2 + y * 2 ** 1 + x * 2 ** 0
                       for y in range(2)]
                      for x in range(2)]
                     for z in range(2)]
                    for c in range(2)]

        np.testing.assert_array_equal(tile, expected)

        size = (1, 1, 1, 1)
        for c, z, x, y in itertools.product(range(2), repeat=4):
            pos = (c, z, x, y)
            tile = conn.get_tile(image_nr=image_nr, pos=pos, size=size)
            v = c * 2 ** 3 + z * 2 ** 2 + y * 2 ** 1 + x * 2 ** 0
            np.testing.assert_array_equal(tile, [[[[v]]]])

    def test_load_label_filenames(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/*.tif')

        c = TiffConnector(img_path, label_path)

        self.assertEqual(c.filenames[0][1],
                         Path('40width26height3slices_rgb.tif'))
        self.assertIsNone(c.filenames[1][1])
        self.assertEqual(c.filenames[2][1],
                         Path('6width4height3slices_rgb.tif'))

    def test_label_tile(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/labels_multichannel/*.tif')

        c = TiffConnector(img_path, label_path)

        label_value = 2
        pos_zxy = (0, 0, 0)
        size_zxy = (1, 6, 4)

        tile = c.label_tile(2, pos_zxy, size_zxy, label_value)

        val_z0 = np.array(
            [[[False, False, False, False],
              [False, False, False, False],
              [False, True,  True,  True],
              [False, True,  True,  True],
              [False, False, False, False],
              [False, False, False, False]]])
        assert_array_equal(val_z0, tile)

        print('First test done!')

        pos_zxy = (1, 0, 0)
        size_zxy = (1, 6, 4)

        tile_z1 = c.label_tile(2, pos_zxy, size_zxy, label_value)

        val_z1 = np.array(
            [[[False, False, False, False],
              [False, False, False, False],
              [False, False, False, False],
              [False, False, False, False],
              [False, False, False, False],
              [True,  True,  False, False]]])
        assert_array_equal(val_z1, tile_z1)

    def test_check_label_matrix_dimensions(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/labels_multichannel/*.tif')

        c = TiffConnector(img_path, label_path)
        c.check_label_matrix_dimensions()

    def test_check_label_matrix_dimensions_2(self):
        img_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/labels_multichannel_not_valid/')

        self.assertRaises(AssertionError, lambda: TiffConnector(
                                                    img_path,
                                                    label_path))

    def test_label_count_for_image(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/*.tif')

        c = TiffConnector(img_path, label_path)

        count = c.label_count_for_image(2)
        print(c.labelvalue_mapping)

        self.assertEqual(count, {2: 11, 3: 3})

    def test_put_tile_multichannel(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/*.tif')
        savepath = tempfile.TemporaryDirectory()
        # savepath = os.path.join(
        #     base_path, '../test_data')

        path = os.path.join(
            savepath.name, '6width4height3slices.tif')

        c = TiffConnector(img_path, label_path, savepath=savepath.name)

        pixels = np.array([[[.1, .2, .3],
                            [.4, .5, .6]]], dtype=np.float32)

        label_value = 3
        c.put_tile(pixels,
                   pos_zxy=(0, 1, 1),
                   image_nr=2,
                   label_value=label_value,
                   multichannel=3)

        slices = c._open_probability_map_file(2, 3, multichannel=3)
        print(slices.shape)
        
        probim = np.moveaxis(slices, (0, 1, 2, 3), (1, 3, 2, 0))
        probim = probim[2:3, :, :, :]

        val = \
            np.array([[[[0., 0., 0., 0.],
                        [0., 0.1, 0.2, 0.3],
                        [0., 0.4, 0.5, 0.6],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]]]], dtype=np.float32)
        print(savepath)
        np.testing.assert_array_equal(val, probim)

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def test_put_tile_1(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/*.tif')
        savepath = tempfile.TemporaryDirectory()

        c = TiffConnector(img_path, label_path, savepath=savepath.name)

        pixels = np.array([[[.1, .2, .3],
                            [.4, .5, .6]]], dtype=np.float32)

        path = os.path.join(
            savepath.name, '6width4height3slices_rgb_class_3.tif')

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

        c.put_tile(pixels, pos_zxy=(0,   1, 1), image_nr=2, label_value=3)

        slices = c._open_probability_map_file(2, 3)
        
        probim = np.moveaxis(slices, (0, 1, 2, 3), (1, 3, 2, 0))

        val = \
            np.array([[[[0., 0., 0., 0.],
                        [0., 0.1, 0.2, 0.3],
                        [0., 0.4, 0.5, 0.6],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]]]], dtype=np.float32)

        np.testing.assert_array_equal(val, probim)

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def test_put_tile_2(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/*.tif')
        savepath = tempfile.TemporaryDirectory()

        c = TiffConnector(img_path, label_path, savepath=savepath.name)

        pixels = np.array([[[.1, .2, .3],
                            [.4, .5, .6]]], dtype=np.float32)

        path = os.path.join(
            savepath.name, '6width4height3slices_rgb_class_3.tif')

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

        c.put_tile(pixels, pos_zxy=(0, 1, 1), image_nr=2, label_value=3)

        slices = c._open_probability_map_file(2, 3)
        
        probim = np.moveaxis(slices, (0, 1, 2, 3), (1, 3, 2, 0))

        val = \
            np.array([[[[0., 0., 0., 0.],
                        [0., 0.1, 0.2, 0.3],
                        [0., 0.4, 0.5, 0.6],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]]]], dtype=np.float32)

        np.testing.assert_array_equal(val, probim)

        c.put_tile(pixels, pos_zxy=(2, 1, 1), image_nr=2, label_value=3)

        slices = c._open_probability_map_file(2, 3)
        
        probim_2 = np.moveaxis(slices, (0, 1, 2, 3), (1, 3, 2, 0))

        val_2 = \
            np.array([[[[0., 0., 0., 0.],
                        [0., 0.1, 0.2, 0.3],
                        [0., 0.4, 0.5, 0.6],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]],
                       [[0., 0., 0., 0.],
                        [0., 0.1, 0.2, 0.3],
                        [0., 0.4, 0.5, 0.6],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.],
                        [0., 0., 0., 0.]]]], dtype=np.float32)

        np.testing.assert_array_equal(val_2, probim_2)

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def test_original_label_values(self):
        img_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/im/*.tif')
        label_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/labels_multichannel/*.tif')

        c = TiffConnector(img_path, label_path)

        res = c.original_label_values_for_all_images()
        self.assertEqual(res, [{91, 109, 150}, {91, 109, 150}])

    def test_map_label_values(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels_multichannel/')
        c = TiffConnector(img_path, label_path)

        original_labels = c.original_label_values_for_all_images()
        res = c.calc_label_values_mapping(original_labels)
        self.assertEqual(res, [{91: 1, 109: 2, 150: 3},
                               {91: 4, 109: 5, 150: 6}])

    def test_map_label_values_2(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)

        original_labels = c.original_label_values_for_all_images()
        res = c.calc_label_values_mapping(original_labels)
        self.assertEqual(res, [{91: 1, 109: 2, 150: 3}])

    def test_map_label_values_3(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(
            base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)

        original_labels = c.original_label_values_for_all_images()
        res = c.calc_label_values_mapping(original_labels)
        self.assertEqual(res, [{91: 1, 109: 2, 150: 3}])

    def test_map_label_values_4(self):

        img_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/im/6width4height3slices_rgb.tif')
        label_path = os.path.join(
            base_path,
            '../test_data/tiffconnector_1/labels/*.tif')

        c = TiffConnector(img_path, label_path)

        original_labels = c.original_label_values_for_all_images()
        c.calc_label_values_mapping(original_labels)
        self.assertEqual(c.labelvalue_mapping, [{109: 1, 150: 2}])
