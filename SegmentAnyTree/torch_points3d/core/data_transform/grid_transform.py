from typing import *
import numpy as np
import random
import scipy
import re
import torch
import logging
import torch.nn.functional as F
from torch_scatter import scatter_mean, scatter_add
from torch_geometric.nn.pool.consecutive import consecutive_cluster
from torch_geometric.nn import voxel_grid
from torch_cluster import grid_cluster
# import mpu.ml

log = logging.getLogger(__name__)


# Label will be the majority label in each voxel
_INTEGER_LABEL_KEYS = ["y", "instance_labels"]


def shuffle_data(data):
    num_points = data.pos.shape[0]
    shuffle_idx = torch.randperm(num_points)
    for key in set(data.keys):
        item = data[key]
        if torch.is_tensor(item) and num_points == item.shape[0]:
            data[key] = item[shuffle_idx]
    return data


def group_data(data, cluster=None, unique_pos_indices=None, mode="last", skip_keys=[]):
    """Group data based on indices in cluster.
    The option ``mode`` controls how data gets agregated within each cluster.
    Parameters
    ----------
    data : Data
        [description]
    cluster : torch.Tensor
        Tensor of the same size as the number of points in data. Each element is the cluster index of that point.
    unique_pos_indices : torch.tensor
        Tensor containing one index per cluster, this index will be used to select features and labels
    mode : str
        Option to select how the features and labels for each voxel is computed. Can be ``last`` or ``mean``.
        ``last`` selects the last point falling in a voxel as the representent, ``mean`` takes the average.
    skip_keys: list
        Keys of attributes to skip in the grouping
    """

    assert mode in ["mean", "last"]
    if mode == "mean" and cluster is None:
        raise ValueError("In mean mode the cluster argument needs to be specified")
    if mode == "last" and unique_pos_indices is None:
        raise ValueError(
            "In last mode the unique_pos_indices argument needs to be specified"
        )

    num_nodes = data.num_nodes
    for key, item in data:
        if bool(re.search("edge", key)):
            raise ValueError("Edges not supported. Wrong data type.")
        if key in skip_keys:
            continue

        if torch.is_tensor(item) and item.size(0) == num_nodes:
            if mode == "last" or key == "batch" or key == SaveOriginalPosId.KEY:
                data[key] = item[unique_pos_indices]
            elif mode == "mean":
                is_item_bool = item.dtype == torch.bool
                if is_item_bool:
                    item = item.int()
                if key in _INTEGER_LABEL_KEYS:
                    item_min = item.min()
                    item = F.one_hot(
                        (item - item_min).to(torch.int64)
                    )  # F.one_hot(item - item_min)
                    item = scatter_add(item, cluster, dim=0)
                    data[key] = item.argmax(dim=-1) + item_min
                else:
                    data[key] = scatter_mean(item, cluster, dim=0)
                if is_item_bool:
                    data[key] = data[key].bool()
    return data


def group_data2(data, cluster=None, unique_pos_indices=None, mode="last", skip_keys=[]):
    """Group data based on indices in cluster.
    The option ``mode`` controls how data gets agregated within each cluster.

    Parameters
    ----------
    data : Data
        [description]
    cluster : torch.Tensor
        Tensor of the same size as the number of points in data. Each element is the cluster index of that point.
    unique_pos_indices : torch.tensor
        Tensor containing one index per cluster, this index will be used to select features and labels
    mode : str
        Option to select how the features and labels for each voxel is computed. Can be ``last`` or ``mean``.
        ``last`` selects the last point falling in a voxel as the representent, ``mean`` takes the average.
    skip_keys: list
        Keys of attributes to skip in the grouping
    """

    assert mode in ["mean", "last"]
    if mode == "mean" and cluster is None:
        raise ValueError("In mean mode the cluster argument needs to be specified")
    if mode == "last" and unique_pos_indices is None:
        raise ValueError(
            "In last mode the unique_pos_indices argument needs to be specified"
        )

    num_nodes = data.num_nodes
    for key, item in data:
        if bool(re.search("edge", key)):
            raise ValueError("Edges not supported. Wrong data type.")
        if key in skip_keys:
            continue

        if torch.is_tensor(item) and item.size(0) == num_nodes:
            if mode == "last" or key == "batch" or key == SaveOriginalPosId.KEY:
                data[key] = item[unique_pos_indices]
            elif mode == "mean":
                is_item_bool = item.dtype == torch.bool
                if is_item_bool:
                    item = item.int()
                if key in _INTEGER_LABEL_KEYS:
                    item_min = item.min()
                    # print(key)
                    # print(len(item))
                    # print(item.size())

                    torch.set_printoptions(profile="full")
                    print(item[0])
                    print(cluster[0])
                    item_0 = item - item_min
                    # item = mpu.ml.indices2one_hot(item, nb_classes=item.max()+1)
                    # item = torch.zeros([len(item), item.max()+1], dtype=torch.int32).scatter_(1, item.unsqueeze(1).to(torch.int64), 1)
                    # item = F.one_hot((item - item_min).to(torch.int64))
                    m_zeros = torch.zeros(
                        [len(item_0), item_0.max() + 1], dtype=torch.int32
                    )
                    m_zeros[np.arange(len(item_0)), item_0.to(torch.int64)] = 1
                    # item = item.to(torch.int32)
                    item = m_zeros.clone().detach()

                    # print(torch.sum(item))
                    item = scatter_add(item, cluster, dim=0)
                    data[key] = item.argmax(dim=-1) + item_min
                else:
                    data[key] = scatter_mean(item, cluster, dim=0)
                if is_item_bool:
                    data[key] = data[key].bool()
    return data


class GridSampling3D:
    """Clusters points into voxels with size :attr:`size`.
    Parameters
    ----------
    size: float
        Size of a voxel (in each dimension).
    quantize_coords: bool
        If True, it will convert the points into their associated sparse coordinates within the grid and store
        the value into a new `coords` attribute
    mode: string:
        The mode can be either `last` or `mean`.
        If mode is `mean`, all the points and their features within a cell will be averaged
        If mode is `last`, one random points per cell will be selected with its associated features
    """

    def __init__(
        self,
        size,
        quantize_coords=False,
        mode="mean",
        verbose=False,
        return_inverse=False,
    ):
        self._grid_size = size
        self._quantize_coords = quantize_coords
        self._mode = mode
        self.return_inverse = return_inverse
        if verbose:
            log.warning(
                "If you need to keep track of the position of your points, use SaveOriginalPosId transform before using GridSampling3D"
            )

            if self._mode == "last":
                log.warning(
                    "The tensors within data will be shuffled each time this transform is applied. Be careful that if an attribute doesn't have the size of num_points, it won't be shuffled"
                )

    def _process(self, data):
        if self._mode == "last":
            data = shuffle_data(data)

        coords = torch.round((data.pos) / self._grid_size)
        if "batch" not in data:
            cluster = grid_cluster(coords, torch.tensor([1, 1, 1]))
        else:
            cluster = voxel_grid(coords, data.batch, 1)
        cluster, unique_pos_indices = consecutive_cluster(cluster)
        self._mode = "last"
        data = group_data(data, cluster, unique_pos_indices, mode=self._mode)
        if self._quantize_coords:
            data.coords = coords[unique_pos_indices].int()
        if self.return_inverse:
            data.inverse_indices = cluster
        data.grid_size = torch.tensor([self._grid_size])
        return data

    def __call__(self, data):
        if isinstance(data, list):
            data = [self._process(d) for d in data]
        else:
            data = self._process(data)
        return data

    def __repr__(self):
        return "{}(grid_size={}, quantize_coords={}, mode={})".format(
            self.__class__.__name__, self._grid_size, self._quantize_coords, self._mode
        )


from sklearn.decomposition import PCA


class GridSampling3D_PCA:
    """Clusters points into voxels with size :attr:`size`.
    Parameters
    ----------
    size: float
        Size of a voxel (in each dimension).
    quantize_coords: bool
        If True, it will convert the points into their associated sparse coordinates within the grid and store
        the value into a new `coords` attribute
    mode: string:
        The mode can be either `last` or `mean`.
        If mode is `mean`, all the points and their features within a cell will be averaged
        If mode is `last`, one random points per cell will be selected with its associated features
    """

    def __init__(
        self,
        size,
        quantize_coords=False,
        mode="mean",
        verbose=False,
        return_inverse=False,
    ):
        self._grid_size = size
        self._quantize_coords = quantize_coords
        self._mode = mode
        self.return_inverse = return_inverse
        if verbose:
            log.warning(
                "If you need to keep track of the position of your points, use SaveOriginalPosId transform before using GridSampling3D"
            )

            if self._mode == "last":
                log.warning(
                    "The tensors within data will be shuffled each time this transform is applied. Be careful that if an attribute doesn't have the size of num_points, it won't be shuffled"
                )

    def _process(self, data):
        if self._mode == "last":
            data = shuffle_data(data)

        # PCA to find the minimum bounding box of the whole point cloud
        pca = PCA(n_components=2)
        pca.fit(data.pos.numpy()[:, 0:-1])
        data_reduced = data.pos.numpy().copy()
        data_reduced[:, 0:-1] = np.dot(
            data.pos.numpy()[:, 0:-1] - pca.mean_, pca.components_.T
        )  # transform

        coords = np.round((data_reduced) / self._grid_size)
        # coords = np.dot(coords, pca.components_) + pca.mean_ # inverse_transform
        coords[:, -1] = 0
        coords[:, 0:-1] = (
            np.dot(coords[:, 0:-1], pca.components_) + pca.mean_
        )  # inverse_transform
        coords = torch.tensor(coords)

        if "batch" not in data:
            # cluster = grid_cluster(coords, torch.tensor([1, 1, 1]), torch.min(coords,0)[0], torch.max(coords,0)[0])
            cluster = grid_cluster(coords[:, 0:-1], torch.tensor([1, 1]))
        else:
            cluster = voxel_grid(coords, data.batch, 1)
        cluster, unique_pos_indices = consecutive_cluster(cluster)
        self._mode = "last"
        data = group_data(data, cluster, unique_pos_indices, mode=self._mode)
        if self._quantize_coords:
            data.coords = coords[unique_pos_indices].int()
        if self.return_inverse:
            data.inverse_indices = cluster
        data.grid_size = torch.tensor([self._grid_size])

        return data

    def __call__(self, data):
        if isinstance(data, list):
            data = [self._process(d) for d in data]
        else:
            data = self._process(data)
        return data

    def __repr__(self):
        return "{}(grid_size={}, quantize_coords={}, mode={})".format(
            self.__class__.__name__, self._grid_size, self._quantize_coords, self._mode
        )


class SaveOriginalPosId:
    """Transform that adds the index of the point to the data object
    This allows us to track this point from the output back to the input data object
    """

    KEY = "origin_id"

    def _process(self, data):
        if hasattr(data, self.KEY):
            return data

        setattr(data, self.KEY, torch.arange(0, data.pos.shape[0]))
        return data

    def __call__(self, data):
        if isinstance(data, list):
            data = [self._process(d) for d in data]
        else:
            data = self._process(data)
        return data

    def __repr__(self):
        return self.__class__.__name__


class SaveLocalOriginalPosId:
    """Transform that adds the index of the point to the data object
    This allows us to track this point from the output back to the input data object
    """

    KEY = "local_id"

    def _process(self, data):
        if hasattr(data, self.KEY):
            return data

        setattr(data, self.KEY, torch.arange(0, data.pos.shape[0]))
        return data

    def __call__(self, data):
        if isinstance(data, list):
            data = [self._process(d) for d in data]
        else:
            data = self._process(data)
        return data

    def __repr__(self):
        return self.__class__.__name__


class ElasticDistortion:
    """Apply elastic distortion on sparse coordinate space. First projects the position onto a
    voxel grid and then apply the distortion to the voxel grid.

    Parameters
    ----------
    granularity: List[float]
        Granularity of the noise in meters
    magnitude:List[float]
        Noise multiplier in meters
    Returns
    -------
    data: Data
        Returns the same data object with distorted grid
    """

    def __init__(
        self,
        apply_distorsion: bool = True,
        granularity: List = [0.2, 0.8],
        magnitude=[0.4, 1.6],
    ):
        assert len(magnitude) == len(granularity)
        self._apply_distorsion = apply_distorsion
        self._granularity = granularity
        self._magnitude = magnitude

    @staticmethod
    def elastic_distortion(coords, granularity, magnitude):
        coords = coords.numpy()
        blurx = np.ones((3, 1, 1, 1)).astype("float32") / 3
        blury = np.ones((1, 3, 1, 1)).astype("float32") / 3
        blurz = np.ones((1, 1, 3, 1)).astype("float32") / 3
        coords_min = coords.min(0)

        # Create Gaussian noise tensor of the size given by granularity.
        noise_dim = ((coords - coords_min).max(0) // granularity).astype(int) + 3
        noise = np.random.randn(*noise_dim, 3).astype(np.float32)

        # Smoothing.
        for _ in range(2):
            noise = scipy.ndimage.filters.convolve(
                noise, blurx, mode="constant", cval=0
            )
            noise = scipy.ndimage.filters.convolve(
                noise, blury, mode="constant", cval=0
            )
            noise = scipy.ndimage.filters.convolve(
                noise, blurz, mode="constant", cval=0
            )

        # Trilinear interpolate noise filters for each spatial dimensions.
        ax = [
            np.linspace(d_min, d_max, d)
            for d_min, d_max, d in zip(
                coords_min - granularity,
                coords_min + granularity * (noise_dim - 2),
                noise_dim,
            )
        ]
        interp = scipy.interpolate.RegularGridInterpolator(
            ax, noise, bounds_error=0, fill_value=0
        )
        coords = coords + interp(coords) * magnitude
        return torch.tensor(coords).float()

    def __call__(self, data):
        # coords = data.pos / self._spatial_resolution
        if self._apply_distorsion:
            if random.random() < 0.95:
                for i in range(len(self._granularity)):
                    data.pos = ElasticDistortion.elastic_distortion(
                        data.pos,
                        self._granularity[i],
                        self._magnitude[i],
                    )
        return data

    def __repr__(self):
        return "{}(apply_distorsion={}, granularity={}, magnitude={})".format(
            self.__class__.__name__,
            self._apply_distorsion,
            self._granularity,
            self._magnitude,
        )
