from unittest import TestCase
import os
from pprint import pprint
import numpy as np
from numpy.testing import assert_array_equal
from yapic_io.tiff_connector import TiffConnector
import yapic_io.image_importers as ip
import logging
from pprint import pprint
logger = logging.getLogger(os.path.basename(__file__))

base_path = os.path.dirname(__file__)

class TestTiffconnector(TestCase):
    def test_load_filenames(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        c = TiffConnector(img_path,'path/to/nowhere/')

        img_filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]

        c.load_img_filenames()
        fnames = [e[0] for e in c.filenames]
        img_fnames = [e[0] for e in img_filenames]
        print('c filenames:')
        print(c.filenames)
        print('fnames')
        print(fnames)
        print(set(fnames))
        self.assertEqual(set(img_fnames), set(fnames))


    


    def test_load_filenames_from_same_path(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/together/img*.tif')
        lbl_path = os.path.join(base_path, '../test_data/tiffconnector_1/together/lbl*.tif')
        c = TiffConnector(img_path, lbl_path)
        
        print(c.filenames)
        
        
        expected_names = \
            [['img_40width26height3slices_rgb.tif', 'lbl_40width26height3slices_rgb.tif']\
           , ['img_40width26height6slices_rgb.tif', None]\
           , ['img_6width4height3slices_rgb.tif', 'lbl_6width4height3slices_rgb.tif']]

        self.assertEqual(c.filenames, expected_names)   



    def test_load_filenames_emptyfolder(self):
        img_path = os.path.join(base_path, '../test_data/empty_folder/')
        c = TiffConnector(img_path,'path/to/nowhere/')
        #c.load_img_filenames()
        self.assertIsNone(c.filenames)


    def test_load_img_dimensions(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        c = TiffConnector(img_path,'path/to/nowhere/')
        
        c.filenames = [\
                ('6width4height3slices_rgb.tif',)\
                , ('40width26height3slices_rgb.tif',)\
                , ('40width26height6slices_rgb.tif',)\
                ]


        
        self.assertFalse(c.load_img_dimensions(-1))
        self.assertFalse(c.load_img_dimensions(4))   
        
        self.assertEqual(c.load_img_dimensions(0), (3, 3, 6, 4))   
        self.assertEqual(c.load_img_dimensions(1), (3, 3, 40, 26))
        self.assertEqual(c.load_img_dimensions(2), (3, 6, 40, 26))


    def test_load_image(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        c = TiffConnector(img_path,'path/to/nowhere/')
        
        im = c.load_image(0)
        print(im)
        
        self.assertEqual(im.shape, (3, 3, 40, 26))


    def test_get_template(self):
        
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        c = TiffConnector(img_path,'path/to/nowhere/')
        

        image_nr = 0
        pos = (0, 0, 0, 0)
        size = (1, 1, 1, 2)
        im = c.load_image(0)
        tpl = c.get_template(image_nr=image_nr, pos=pos, size=size)
        val = np.empty(shape=size)
        val[0,0,0,0] = 151
        val[0,0,0,1] = 151
        val = val.astype(int)
        print(val)
        print(tpl)
        np.testing.assert_array_equal(tpl, val)


    def test_exists_label_for_image_nr(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]    
        c.load_label_filenames()        
        self.assertFalse(c.exists_label_for_img(2))
        self.assertTrue(c.exists_label_for_img(0))
        self.assertTrue(c.exists_label_for_img(1))

    def test_load_label_filenames(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]    
        print(c.filenames)
        c.load_label_filenames()
        print(c.filenames)
        self.assertIsNone(c.filenames[2][1])
        self.assertEqual(c.filenames[1][1], '40width26height3slices_rgb.tif')
        self.assertEqual(c.filenames[0][1], '6width4height3slices_rgb.tif')
        #self.assertTrue(False)
    

    def test_load_label_matrix(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]    
        print(c.filenames)
        c.load_label_filenames()
        im = c.load_image(0)
        labelmat = c.load_label_matrix(0)
        print(labelmat)
        self.assertEqual(labelmat.shape, (1, 3, 6, 4))

    def test_load_label_matrix_multichannel(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels_multichannel/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]    
        print(c.filenames)
        c.load_label_filenames()
        im = c.load_image(0)
        labelmat = c.load_label_matrix(0)
        print(labelmat)
        print(c.labelvalue_mapping)
        self.assertEqual(labelmat.shape, (2, 3, 6, 4)) 

    def test_get_template_for_label(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels_multichannel/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]    
        print(c.filenames)
        c.load_label_filenames()

        label_value = 2

        pos_zxy = (0,0,0)
        size_zxy = (1,6,4)

        tpl = c.get_template_for_label(0, pos_zxy, size_zxy, label_value)
        print(tpl)
        print(tpl.shape)


        val_z0 = np.array(\
        [[[False, False, False, False],
          [False, False, False, False],
          [False,  True,  True,  True],
          [False,  True,  True,  True],
          [False, False, False, False],
          [False, False, False, False]]])

        assert_array_equal(val_z0,tpl)


        pos_zxy = (1,0,0)
        size_zxy = (1,6,4)

        tpl_z1 = c.get_template_for_label(0, pos_zxy, size_zxy, label_value)
        print(tpl_z1)
        print(tpl_z1.shape)


        val_z1 = np.array(\
        [[[False, False, False, False],
          [False, False, False, False],
          [False, False, False, False],
          [False, False, False, False],
          [False, False, False, False],
          [ True,  True, False, False]]])

        assert_array_equal(val_z1,tpl_z1)


            

    def test_check_labelmat_dimensions(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]    
        print(c.filenames)
        c.load_label_filenames()
        c.check_labelmat_dimensions()
        


    def test_check_labelmat_dimensions_2(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels_multichannel_not_valid/')
    
        
        self.assertRaises(ValueError, lambda: TiffConnector(img_path, label_path))    


    def test_get_labelvalues_for_im(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]
        c.load_label_filenames()            
        labelvals = c.get_labelvalues_for_im(0)

        print('lbklals')
        print(labelvals)
        self.assertEqual(labelvals, [2, 3])


    # def test_get_label_coordinates(self):
    #     img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
    #     label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
    #     c = TiffConnector(img_path, label_path)
        
    #     c.filenames = [\
    #             ['6width4height3slices_rgb.tif', None]\
    #             , ['40width26height3slices_rgb.tif', None]\
    #             , ['40width26height6slices_rgb.tif', None]\
    #             ]
    #     c.load_label_filenames()            
    #     labelc = c.get_label_coordinates(0)
    #     labelmat = c.load_label_matrix(0)
        
    #     #label mapping [{91: 1, 109: 2, 150: 3}]               
    #     val_109 =np.array(\
    #        [(0, 0, 2, 1), (0, 0, 2, 2), (0, 0, 2, 3)\
    #        , (0, 0, 3, 1), (0, 0, 3, 2), (0, 0, 3, 3)\
    #        , (0, 1, 5, 0), (0, 1, 5, 1), (0, 2, 0, 0)\
    #        , (0, 2, 1, 0), (0, 2, 1, 2)])

    #     val_150 =np.array(\
    #         [(0, 0, 0, 1), (0, 0, 4, 1), (0, 0, 5, 1)])   

    #     print('109')
    #     print(labelc[2])
    #     print('150')
    #     print(labelc[3])

    #     print(labelmat)
    #     print(labelmat.shape)
    #     self.assertTrue((val_109 == labelc[2]).all())
    #     self.assertTrue((val_150 == labelc[3]).all())


    def test_get_label_coordinate(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]
        c.load_label_filenames()            
        

        label_value = 2 #wrong labelvalue
        label_index = 10
        image_nr = 0
        print(c.labelvalue_mapping)
        
        #self.assertTrue(c.get_label_coordinate(image_nr, label_value, 10)
        assert_array_equal(c.get_label_coordinate(image_nr, label_value, 10), np.array([0,2,1,2]))
        assert_array_equal(c.get_label_coordinate(image_nr, label_value, 9), np.array([0,2,1,0]))
        assert_array_equal(c.get_label_coordinate(image_nr, label_value, 0), np.array([0,0,2,1]))    
        #self.assertTrue(False)    
    

    def test_get_labelcount_for_im(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]
        c.load_label_filenames()            
                    
        count = c.get_labelcount_for_im(0)
        print(c.labelvalue_mapping)

        self.assertEqual(count, {2 : 11, 3: 3})



    
        
        

        
    
    

    def test_get_probmap_path(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path, savepath = 'path/to/probmaps')
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]


        p = c.get_probmap_path(0,3)

        self.assertEqual(p, 'path/to/probmaps/6width4height3slices_rgb_class_3.tif')


    def test_get_probmap_path_2(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path, savepath = 'path/to/probmaps/')
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]


        p = c.get_probmap_path(0,3)

        self.assertEqual(p, 'path/to/probmaps/6width4height3slices_rgb_class_3.tif')


    

    def test_init_probmap_image(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        savepath = os.path.join(base_path, '../test_data/tmp/')
        


        c = TiffConnector(img_path, label_path, savepath = savepath)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]

        

        path1 = savepath + '6width4height3slices_rgb_class_1.tif'
        path2 = savepath + '6width4height3slices_rgb_class_2.tif'
        
        try:
            os.remove(path1)
        except:
            pass

        try:
            os.remove(path2)
        except:
            pass    

        c.init_probmap_image(0,1, overwrite=True)
        c.init_probmap_image(0,2, overwrite=True)    
            
        probim_1 = ip.import_tiff_image(path1, zstack=True)
        probim_2 = ip.import_tiff_image(path2, zstack=True)


        self.assertEqual(probim_1.shape, (1,3,6,4))
        self.assertEqual(probim_2.shape, (1,3,6,4))

        try:
            os.remove(path1)
        except:
            pass

        try:
            os.remove(path2)
        except:
            pass    

    def test_put_template_1(self):

        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        savepath = os.path.join(base_path, '../test_data/tmp/')
        


        c = TiffConnector(img_path, label_path, savepath = savepath)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]

        pixels = np.array([[[.1, .2, .3],\
                            [.4, .5, .6]]], dtype=np.float32)
        
        path = savepath + '6width4height3slices_rgb_class_3.tif'
        
        try:
            os.remove(path)
        except:
            pass    

        c.put_template(pixels, pos_zxy=(0,1,1), image_nr=0, label_value=3)
        probim = ip.import_tiff_image(path, zstack=True)
        pprint(probim)

        val = \
        np.array([[[[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.1       ,  0.2       ,  0.3       ],\
         [ 0.        ,  0.4       ,  0.5       ,  0.6       ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]],\
        [[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]],\
        [[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]]]], dtype=np.float32)
        
        self.assertTrue((val==probim).all())

        try:
            os.remove(path)
        except:
            pass    

        

    def test_put_template_2(self):

        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        savepath = os.path.join(base_path, '../test_data/tmp/')
        


        c = TiffConnector(img_path, label_path, savepath = savepath)
        
        c.filenames = [\
                ['6width4height3slices_rgb.tif', None]\
                , ['40width26height3slices_rgb.tif', None]\
                , ['40width26height6slices_rgb.tif', None]\
                ]

        pixels = np.array([[[.1, .2, .3],\
                            [.4, .5, .6]]], dtype=np.float32)
        
        path = savepath + '6width4height3slices_rgb_class_3.tif'
        
        try:
            os.remove(path)
        except:
            pass    

        c.put_template(pixels, pos_zxy=(0,1,1), image_nr=0, label_value=3)
        probim = ip.import_tiff_image(path, zstack=True)
        pprint(probim)

        val = \
        np.array([[[[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.1       ,  0.2       ,  0.3       ],\
         [ 0.        ,  0.4       ,  0.5       ,  0.6       ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]],\
        [[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]],\
        [[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]]]], dtype=np.float32)
        
        self.assertTrue((val==probim).all())


        c.put_template(pixels, pos_zxy=(2,1,1), image_nr=0, label_value=3)
        probim_2 = ip.import_tiff_image(path, zstack=True)
        pprint(probim_2)

        val_2 = \
        np.array([[[[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.1       ,  0.2       ,  0.3       ],\
         [ 0.        ,  0.4       ,  0.5       ,  0.6       ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]],\
        [[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]],\
        [[ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.1       ,  0.2       ,  0.3        ],\
         [ 0.        ,  0.4       ,  0.5       ,  0.6        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ],\
         [ 0.        ,  0.        ,  0.        ,  0.        ]]]], dtype=np.float32)

        self.assertTrue((val_2==probim_2).all())    

        try:
            os.remove(path)
        except:
            pass    

    


    def test_get_original_labelvalues_for_im(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)

        res = c.get_original_labelvalues_for_im(0)
        self.assertEqual(res, [{91, 109, 150}])
        res = c.get_original_labelvalues_for_im(1)
        self.assertIsNone(res)
        res = c.get_original_labelvalues_for_im(2)
        
        self.assertEqual(res, [{109, 150}])

    def test_get_original_labelvalues_for_im_2(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels_multichannel/')
        c = TiffConnector(img_path, label_path)

        res = c.get_original_labelvalues_for_im(0)
        self.assertEqual(res, [{91, 109, 150}, {91, 109, 150}])
        res = c.get_original_labelvalues_for_im(1)
        self.assertIsNone(res)
        res = c.get_original_labelvalues_for_im(2)
        
        self.assertEqual(res, [{109, 150}, {109, 150}])

    def test_get_original_labelvalues(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels_multichannel/')
        c = TiffConnector(img_path, label_path)

        res = c.get_original_labelvalues()
        self.assertEqual(res, [{91, 109, 150}, {91, 109, 150}])
        

    def test_map_labelvalues(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels_multichannel/')
        c = TiffConnector(img_path, label_path)

        res = c.map_labelvalues()
        self.assertEqual(res, [{91:1, 109:2, 150:3}, {91:4, 109:5, 150:6}])

    def test_map_labelvalues_2(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)

        res = c.map_labelvalues()
        self.assertEqual(res, [{91:1, 109:2, 150:3}])

    def test_map_labelvalues_3(self):
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/')
        c = TiffConnector(img_path, label_path)

        res = c.map_labelvalues()
        self.assertEqual(res, [{91:1, 109:2, 150:3}])


    def test_map_labelvalues_4(self):    
        
        img_path = os.path.join(base_path, '../test_data/tiffconnector_1/im/6width4height3slices_rgb.tif')
        label_path = os.path.join(base_path, '../test_data/tiffconnector_1/labels/*.tif')
        c = TiffConnector(img_path, label_path)

        
        c.load_label_filenames()
        print(c.filenames)
        print(c.labelvalue_mapping)
        c.map_labelvalues()
        print(c.labelvalue_mapping)
        print('origvals')
        print(c.get_original_labelvalues_for_im(0))
        self.assertEqual(c.labelvalue_mapping, [{109: 1, 150: 2}])

    




        


    


