import torch
import numpy as np
from typing import NamedTuple, List


def non_max_suppression(ious, scores, threshold):
    ixs = scores.argsort()[::-1]
    pick = []
    while len(ixs) > 0:
        i = ixs[0]
        pick.append(i)
        iou = ious[i, ixs[1:]]
        remove_ixs = np.where(iou > threshold)[0] + 1
        ixs = np.delete(ixs, remove_ixs)
        ixs = np.delete(ixs, 0)
    return pick


class PanopticResults(NamedTuple):
    semantic_logits: torch.Tensor
    offset_logits: torch.Tensor
    cluster_scores: torch.Tensor  # One float value per cluster
    mask_scores: torch.Tensor  # One float value per point belongs to clusters
    clusters: List[
        torch.Tensor
    ]  # Each item contains the list of indices in the cluster
    cluster_type: torch.Tensor  # Wether a cluster is coming from the votes or the original points. 0->original pos, 1->vote

    def get_instances(
        self, nms_threshold=0.3, min_cluster_points=100, min_score=0.2
    ) -> List:
        """Returns index of clusters that pass nms test, min size test and score test"""
        if not self.clusters:
            return [], []

        if self.cluster_scores == None:
            return None, self.clusters
        _mask = None
        if self.mask_scores != None:
            _mask = self.mask_scores.squeeze(1) > -0.5  # ??
        n_prop = len(self.clusters)
        proposal_masks = torch.zeros(n_prop, self.semantic_logits.shape[0])
        # for i, cluster in enumerate(self.clusters):
        #     proposal_masks[i, cluster] = 1

        proposals_idx = []
        for i, cluster in enumerate(self.clusters):
            proposal_id = torch.ones(len(cluster)).cuda() * i
            proposals_idx.append(torch.vstack((proposal_id, cluster)).T)
        proposals_idx = torch.cat(proposals_idx, dim=0)
        if _mask != None:
            proposals_idx_filtered = proposals_idx[_mask]
        else:
            proposals_idx_filtered = proposals_idx
        proposal_masks[
            proposals_idx_filtered[:, 0].long(), proposals_idx_filtered[:, 1].long()
        ] = 1

        intersection = torch.mm(
            proposal_masks, proposal_masks.t()
        )  # (nProposal, nProposal), float, cuda
        proposals_pointnum = proposal_masks.sum(1)  # (nProposal), float, cuda
        proposals_pn_h = proposals_pointnum.unsqueeze(-1).repeat(
            1, proposals_pointnum.shape[0]
        )
        proposals_pn_v = proposals_pointnum.unsqueeze(0).repeat(
            proposals_pointnum.shape[0], 1
        )
        cross_ious = intersection / (proposals_pn_h + proposals_pn_v - intersection)
        pick_idxs = non_max_suppression(
            cross_ious.cpu().numpy(), self.cluster_scores.cpu().numpy(), nms_threshold
        )

        valid_pick_ids = []
        valid_clusters = []
        for i in pick_idxs:
            cl_mask = proposals_idx_filtered[:, 0] == i
            cl = proposals_idx_filtered[cl_mask][:, 1].long()
            if len(cl) > min_cluster_points and self.cluster_scores[i] > min_score:
                valid_pick_ids.append(i)
                valid_clusters.append(cl)
        return valid_pick_ids, valid_clusters


class PanopticLabels(NamedTuple):
    center_label: torch.Tensor
    y: torch.Tensor
    num_instances: torch.Tensor
    instance_labels: torch.Tensor
    instance_mask: torch.Tensor
    vote_label: torch.Tensor
