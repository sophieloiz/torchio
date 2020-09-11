from typing import Union, Sequence, List

import torch
import torchio
import numpy as np
from torchvision.transforms import Compose as PyTorchCompose

from ...data.subject import Subject
from ...utils import gen_seed
from .. import Transform
from . import RandomTransform


class Compose(Transform):
    """Compose several transforms together.

    Args:
        transforms: Sequence of instances of
            :py:class:`~torchio.transforms.transform.Transform`.
        p: Probability that this transform will be applied.

    .. note::
        This is a thin wrapper of :py:class:`torchvision.transforms.Compose`.
    """
    def __init__(self, transforms: Sequence[Transform] = [], p: float = 1, **kwargs):
        super().__init__(p=p, **kwargs)
        self.transform = PyTorchCompose(transforms)

    def __call__(self, data: Union[Subject, torch.Tensor, np.ndarray], seeds: List = None):
        if not self.transform.transforms:
            return data

        if not seeds:
            seeds = [gen_seed() for _ in range(len(self.transform.transforms))]
        self.seeds = seeds
        return super(Compose, self).__call__(data, seeds)

    def apply_transform(self, sample: Subject):
        for t, s in zip(self.transform.transforms, self.seeds):
            sample = t(sample, s)
        return sample

class OneOf(RandomTransform):
    """Apply only one of the given transforms.

    Args:
        transforms: Dictionary with instances of
            :py:class:`~torchio.transforms.transform.Transform` as keys and
            probabilities as values. Probabilities are normalized so they sum
            to one. If a sequence is given, the same probability will be
            assigned to each transform.
        p: Probability that this transform will be applied.

    Example:
        >>> import torchio
        >>> ixi = torchio.datasets.ixi.IXITiny('ixi', download=True)
        >>> sample = ixi[0]
        >>> transforms_dict = {
        ...     torchio.transforms.RandomAffine(): 0.75,
        ...     torchio.transforms.RandomElasticDeformation(): 0.25,
        ... }  # Using 3 and 1 as probabilities would have the same effect
        >>> transform = torchio.transforms.OneOf(transforms_dict)

    """
    def __init__(
            self,
            transforms: Union[dict, Sequence[Transform]],
            p: float = 1,
            **kwargs
            ):
        super().__init__(p=p, **kwargs)
        self.transforms_dict = self._get_transforms_dict(transforms)

    def apply_transform(self, sample: Subject):
        weights = torch.Tensor(list(self.transforms_dict.values()))
        index = torch.multinomial(weights, 1)
        transforms = list(self.transforms_dict.keys())
        transform = transforms[index]
        transformed = transform(sample)
        return transformed

    def _get_transforms_dict(self, transforms: Union[dict, Sequence]):
        if isinstance(transforms, dict):
            transforms_dict = dict(transforms)
            self._normalize_probabilities(transforms_dict)
        else:
            try:
                p = 1 / len(transforms)
            except TypeError as e:
                message = (
                    'Transforms argument must be a dictionary or a sequence,'
                    f' not {type(transforms)}'
                )
                raise ValueError(message) from e
            transforms_dict = {transform: p for transform in transforms}
        for transform in transforms_dict:
            if not isinstance(transform, Transform):
                message = (
                    'All keys in transform_dict must be instances of'
                    f'torchio.Transform, not "{type(transform)}"'
                )
                raise ValueError(message)
        return transforms_dict

    @staticmethod
    def _normalize_probabilities(transforms_dict: dict):
        probabilities = np.array(list(transforms_dict.values()), dtype=float)
        if np.any(probabilities < 0):
            message = (
                'Probabilities must be greater or equal to zero,'
                f' not "{probabilities}"'
            )
            raise ValueError(message)
        if np.all(probabilities == 0):
            message = (
                'At least one probability must be greater than zero,'
                f' but they are "{probabilities}"'
            )
            raise ValueError(message)
        for transform, probability in transforms_dict.items():
            transforms_dict[transform] = probability / probabilities.sum()


class ListOf(RandomTransform):
    """Apply sequencly all of the given transforms.

    Args:
        transforms: A list  of
            :py:class:`~torchio.transforms.transform.Transform`
        p : probabilities

    Example:
        >>> import torchio
        >>> ixi = torchio.datasets.ixi.IXITiny('ixi', download=True)
        >>> sample = ixi[0]
        >>> transforms_dict = []
        ...     torchio.transforms.RandomAffine(),
        ...     torchio.transforms.RandomElasticDeformation(),
        ... ]
        >>> transform = torchio.transforms.OneOf(transforms_dict)

    """
    def __init__(
            self,
            transforms: Sequence[Transform],
            p: float = 1,
            **kwargs
            ):
        super().__init__(p=p, **kwargs)
        self.transforms_list = transforms

    def apply_transform(self, sample: Subject):

        transformed_list=[]
        for tt in self.transforms_list:
            transformed_list.append(tt(sample))

        return transformed_list


def compose_from_history(history: List):
    """
    Builds a composition of transformations from a given subject history
    :param history: subject history given as a list of tuples containing (transformation_name, transformation_parameters)
    :return: Tuple (Compose of transforms, list of seeds to reproduce the transforms from the history)
    """
    trsfm_list = []
    seed_list = []
    for trsfm_history in history:
        trsfm_name, trsfm_params = trsfm_history[0], (trsfm_history[1])
        seed_list.append(trsfm_params['seed'])
        trsfm_no_seed = {key: value for key, value in trsfm_params.items() if key != "seed"}
        trsfm_func = getattr(torchio, trsfm_name)()
        trsfm_func.__dict__ = trsfm_no_seed
        trsfm_list.append(trsfm_func)
    return Compose(trsfm_list), seed_list
