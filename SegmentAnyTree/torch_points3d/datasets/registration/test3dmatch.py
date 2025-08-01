import os
import os.path as osp
import torch
import json
from torch_points3d.datasets.base_dataset import BaseDataset
from torch_points3d.datasets.registration.basetest import Base3DMatchTest
from torch_points3d.datasets.registration.basetest import SimplePatch
from torch_points3d.datasets.registration.utils import PatchExtractor
from torch_points3d.datasets.registration.detector import RandomDetector
from torch_points3d.datasets.registration.base_siamese_dataset import GeneralFragment
from torch_points3d.datasets.registration.base_siamese_dataset import BaseSiameseDataset


class Test3DMatch(Base3DMatchTest):
    def __init__(
        self,
        root,
        radius_patch=0.3,
        pre_transform=None,
        pre_filter=None,
        transform=None,
        verbose=False,
        debug=False,
        num_random_pt=5000,
        max_dist_overlap=0.01,
    ):
        super(Test3DMatch, self).__init__(
            root, transform, pre_transform, pre_filter, verbose, debug, max_dist_overlap
        )
        self.num_random_pt = num_random_pt
        self.radius_patch = radius_patch
        self.patch_extractor = PatchExtractor(self.radius_patch)
        self.path_table = osp.join(self.processed_dir, "fragment")
        with open(osp.join(self.path_table, "table.json"), "r") as f:
            self.table = json.load(f)

    def __getitem__(self, idx):
        r"""Gets the data object at index :obj:`idx` and transforms it (in case
        a :obj:`self.transform` is given).
        In case :obj:`idx` is a slicing object, *e.g.*, :obj:`[2:5]`, a list, a
        tuple, a  LongTensor or a BoolTensor, will return a subset of the
        dataset at the specified indices."""
        data = torch.load(osp.join(self.path_table, "fragment_{:06d}.pt".format(idx)))
        if self.transform is not None:
            data = self.transform(data)
        if self.num_random_pt > 0:
            detector = RandomDetector(self.num_random_pt)
            data = detector(data)
        return data

    def get_patches(self, idx):
        fragment = torch.load(
            osp.join(self.path_table, "fragment_{:06d}.pt".format(idx))
        )
        patch_dataset = [
            self.patch_extractor(fragment, fragment.keypoints[i])
            for i in range(self.num_random_pt)
        ]

        simple_patch = SimplePatch(patch_dataset, self.transform)
        return simple_patch

    def __len__(self):
        return len(self.table)

    def len(self):
        return len(self)

    def get_table(self):
        return self.table


class TestPair3DMatch(Base3DMatchTest, GeneralFragment):
    def __init__(
        self,
        root,
        transform=None,
        pre_transform=None,
        pre_filter=None,
        verbose=False,
        debug=False,
        num_pos_pairs=200,
        max_dist_overlap=0.01,
        self_supervised=False,
        ss_transform=None,
        min_size_block=0.3,
        max_size_block=2,
        min_points=500,
        use_fps=False,
    ):
        Base3DMatchTest.__init__(
            self,
            root=root,
            transform=transform,
            pre_transform=pre_transform,
            pre_filter=pre_filter,
            verbose=verbose,
            debug=debug,
            max_dist_overlap=max_dist_overlap,
        )
        self.num_pos_pairs = num_pos_pairs
        self.path_match = osp.join(self.processed_dir, "test", "matches")
        self.list_fragment = [f for f in os.listdir(self.path_match) if "matches" in f]
        self.self_supervised = self_supervised
        self.ss_transform = ss_transform
        self.is_online_matching = False
        self.use_fps = use_fps
        self.min_points = min_points
        self.min_size_block = min_size_block
        self.max_size_block = max_size_block

    def __getitem__(self, idx):
        return self.get_fragment(idx)

    def __len__(self):
        return len(self.list_fragment)

    def len(self):
        return len(self)

    def process(self):
        super().process()

    def download(self):
        super().download()


class TestPair3DMatchDataset(BaseSiameseDataset):
    def __init__(self, dataset_opt):
        super().__init__(dataset_opt)
        pre_transform = self.pre_transform
        ss_transform = getattr(self, "ss_transform", None)
        train_transform = self.train_transform
        test_transform = self.test_transform

        self.train_dataset = TestPair3DMatch(
            root=self._data_path,
            pre_transform=pre_transform,
            transform=train_transform,
            num_pos_pairs=dataset_opt.num_pos_pairs,
            max_dist_overlap=dataset_opt.max_dist_overlap,
            self_supervised=True,
            min_size_block=dataset_opt.min_size_block,
            max_size_block=dataset_opt.max_size_block,
            ss_transform=ss_transform,
            min_points=dataset_opt.min_points,
            use_fps=dataset_opt.use_fps,
        )

        self.test_dataset = TestPair3DMatch(
            root=self._data_path,
            pre_transform=pre_transform,
            transform=test_transform,
            num_pos_pairs=50,
            max_dist_overlap=dataset_opt.max_dist_overlap,
            self_supervised=False,
        )


class Test3DMatchDataset(BaseDataset):
    """
    this class is a dataset just for testing.
    if we compute descriptors on patches,  at each iteration,
    the test dataset must change
    """

    def __init__(self, dataset_opt):
        super().__init__(dataset_opt)
        pre_transform = self.pre_transform
        test_transform = self.test_transform

        self.base_dataset = Test3DMatch(
            root=self._data_path,
            radius_patch=dataset_opt.radius_patch,
            pre_transform=pre_transform,
            transform=test_transform,
            num_random_pt=dataset_opt.num_random_pt,
        )

        if dataset_opt.is_patch:
            self.test_dataset = self.base_dataset.get_patches(0)
        else:
            self.test_dataset = self.base_dataset

    def set_patches(self, idx):
        self.test_dataset = self.base_dataset.get_patches(idx)

    def get_name(self, idx):
        """
        return a pair of string which indicate the name of the scene and
        the name of the point cloud
        """
        table = self.base_dataset.get_table()[str(idx)]
        return table["scene_path"], table["fragment_name"]

    @property
    def num_fragment(self):
        return len(self.base_dataset)
