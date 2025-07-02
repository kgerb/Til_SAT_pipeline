import argparse
import numpy as np
from scipy.spatial import KDTree
import laspy
import os


def main(original_file, subsampled_file, output_file):
    """
    Remap predicted attributes from a subsampled point cloud back to the original resolution point cloud.

    This function takes an original point cloud file and a subsampled point cloud file (both LAS/LAZ),
    and for each point in the original, finds its nearest neighbor in the subsampled cloud. It then
    copies the predicted attributes (e.g., PredInstance, PredSemantic) from the subsampled cloud to the
    original cloud, creating new attributes if necessary. The updated original point cloud is saved to
    the specified output file.

    Args:
        original_file (str): Path to the original resolution LAS/LAZ file.
        subsampled_file (str): Path to the subsampled LAS/LAZ file with predicted attributes.
        output_file (str): Path to save the updated original LAS/LAZ file.
    """
    # Load the original point cloud
    original_las = laspy.read(original_file)
    original_points = np.vstack((original_las.x, original_las.y, original_las.z)).T

    # Load the subsampled point cloud
    subsampled_las = laspy.read(subsampled_file)
    subsampled_points = np.vstack(
        (subsampled_las.x, subsampled_las.y, subsampled_las.z)
    ).T

    # Create new attributes in the original point cloud if they don't exist
    extra_dims = original_las.point_format.extra_dimensions
    existing_dims = {dim.name for dim in extra_dims}

    if "PredInstance" not in existing_dims:
        original_las.add_extra_dim(
            laspy.ExtraBytesParams(name="PredInstance", type=np.int32)
        )
    if "PredSemantic" not in existing_dims:
        original_las.add_extra_dim(
            laspy.ExtraBytesParams(name="PredSemantic", type=np.int32)
        )
    # if "species_id_x" not in existing_dims:
    #     original_las.add_extra_dim(laspy.ExtraBytesParams(name="species_id_x", type=np.int32))

    # Create a KD-tree for the subsampled point cloud
    tree = KDTree(subsampled_points)

    # Find the nearest neighbors in the subsampled point cloud for each point in the original point cloud
    distances, indices = tree.query(original_points)

    # Map attributes from the subsampled point cloud to the original point cloud
    original_las.PredInstance = subsampled_las.PredInstance[indices]
    original_las.PredSemantic = subsampled_las.PredSemantic[indices]
    # original_las.species_id_x = subsampled_las.species_id_x[indices]

    # print a summary of the original point cloud wether it now has every attribute
    print("Original point cloud now has the following attributes:")
    for dim in original_las.point_format.extra_dimensions:
        print(f"{dim.name}: {dim.dtype}")

    # Save the updated original point cloud
    with open(output_file, "wb") as f:
        original_las.write(f)
        f.flush()
        os.fsync(f.fileno())
    print(f"Updated point cloud saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Map attributes from a subsampled point cloud back to the original point cloud."
    )
    parser.add_argument(
        "--original_file", type=str, help="Path to the original point cloud file"
    )
    parser.add_argument(
        "--subsampled_file",
        type=str,
        help="Path to the subsampled point cloud file with attributes",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        help="Path to save the updated original point cloud file",
    )
    args = parser.parse_args()

    main(args.original_file, args.subsampled_file, args.output_file)
