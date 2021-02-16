import SimpleITK as sitk

from .label_transform import LabelTransform


class KeepLargestComponent(LabelTransform):
    r"""Keep only the largest connected component in a binary label map.

    Args:
        **kwargs: See :class:`~torchio.transforms.Transform` for additional
            keyword arguments.

    .. note:: For now, this transform only works for binary images, i.e., label
        maps with a background and a foreground class. If you are interested in
        extending this transform `open a new issue`_.

    .. _open a new issue: https://github.com/fepegar/torchio/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=Improve%20KeepLargestComponent%20transform
    """  # noqa: E501

    def apply_transform(self, subject):
        for image in self.get_images(subject):
            assert image.data.ndim == 4 and image.data.shape[0] == 1
            sitk_image = image.as_sitk()
            connected_components = sitk.ConnectedComponent(sitk_image)
            labeled_cc = sitk.RelabelComponent(connected_components)
            largest_cc = labeled_cc == 1
            tensor, _ = self.sitk_to_nib(largest_cc)
            image.set_data(tensor)
        return subject
