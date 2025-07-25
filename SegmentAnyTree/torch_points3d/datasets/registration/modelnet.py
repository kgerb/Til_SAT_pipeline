from itertools import repeat
import torch


from torch_points3d.datasets.classification.modelnet import SampledModelNet
from torch_points3d.datasets.registration.base_siamese_dataset import BaseSiameseDataset
from torch_points3d.datasets.registration.base_siamese_dataset import GeneralFragment


class SiameseModelNet(SampledModelNet, GeneralFragment):
    r"""
    the ModelNet Dataset from the `"3D ShapeNets: A Deep
    Representation for Volumetric Shapes"
    <https://people.csail.mit.edu/khosla/papers/cvpr2015_wu.pdf>`_ paper,
    containing sampled CAD models of 40 categories. Each sample contains 10,000
    points uniformly sampled with their normal vector.

    But applied for registration.
    Only the self supervised mode is supported
    """

    def __init__(
        self,
        root,
        name_modelnet="10",
        min_size_block=0.3,
        max_size_block=2,
        max_dist_overlap=0.1,
        train=True,
        transform=None,
        pre_transform=None,
        pre_filter=None,
        num_pos_pairs=1024,
        ss_transform=None,
        min_points=500,
        use_fps=False,
    ):
        SampledModelNet.__init__(
            self, root, name_modelnet, train, transform, pre_transform, pre_filter
        )
        self.self_supervised = True  # only self supervised is allowed for modelnet
        self.is_online_matching = False
        self.num_pos_pairs = num_pos_pairs
        self.min_size_block = min_size_block
        self.max_size_block = max_size_block
        self.max_dist_overlap = max_dist_overlap
        self.ss_transform = ss_transform
        self.min_points = min_points
        self.train = train
        self.use_fps = use_fps
        if self.train:
            self.name = "train"
        else:
            self.name = "test"

    def get_model(self, idx):
        data = self.data.__class__()

        if hasattr(self.data, "__num_nodes__"):
            data.num_nodes = self.data.__num_nodes__[idx]

        for key in self.data.keys:
            item, slices = self.data[key], self.slices[key]
            start, end = slices[idx].item(), slices[idx + 1].item()
            # print(slices[idx], slices[idx + 1])
            if torch.is_tensor(item):
                s = list(repeat(slice(None), item.dim()))
                s[self.data.__cat_dim__(key, item)] = slice(start, end)
            elif start + 1 == end:
                s = slices[start]
            else:
                s = slice(start, end)
            data[key] = item[s]
        return data

    def get_raw_pair(self, idx):
        """ """
        data_source_o = self.get_model(idx)
        data_target_o = self.get_model(idx)
        data_source, data_target, new_pair = self.unsupervised_preprocess(
            data_source_o, data_target_o
        )
        return data_source, data_target, new_pair

    def __getitem__(self, idx):
        res = self.get_fragment(idx)
        return res

    def get_name(self, idx):
        data = self.get_model(idx)
        return data.y.item(), "{}_source".format(idx), "{}_target".format(idx)

    def process(self):
        super().process()

    def download(self):
        super().download()


class SiameseModelNetDataset(BaseSiameseDataset):
    def __init__(self, dataset_opt):
        super().__init__(dataset_opt)
        pre_transform = self.pre_transform
        ss_transform = getattr(self, "ss_transform", None)
        train_transform = self.train_transform
        test_transform = self.test_transform
        pre_filter = self.pre_filter

        self.train_dataset = SiameseModelNet(
            root=self._data_path,
            name_modelnet=dataset_opt.name_modelnet,
            train=True,
            min_size_block=dataset_opt.min_size_block,
            max_size_block=dataset_opt.max_size_block,
            max_dist_overlap=dataset_opt.max_dist_overlap,
            pre_transform=pre_transform,
            transform=train_transform,
            pre_filter=pre_filter,
            num_pos_pairs=dataset_opt.num_pos_pairs,
            ss_transform=ss_transform,
            min_points=dataset_opt.min_points,
            use_fps=dataset_opt.use_fps,
        )

        self.test_dataset = SiameseModelNet(
            root=self._data_path,
            name_modelnet=dataset_opt.name_modelnet,
            train=False,
            min_size_block=dataset_opt.min_size_block,
            max_size_block=dataset_opt.max_size_block,
            max_dist_overlap=dataset_opt.max_dist_overlap,
            pre_transform=pre_transform,
            transform=test_transform,
            pre_filter=pre_filter,
            num_pos_pairs=dataset_opt.num_pos_pairs,
            min_points=dataset_opt.min_points,
        )
