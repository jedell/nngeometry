from nngeometry.pspace import M2Gradients
from nngeometry.representations import BlockDiagMatrix, KFACMatrix, EKFACMatrix
import torch
from test_m2gradients import get_fullyconnect_task, get_convnet_task
from nngeometry.vector import random_pvector
from utils import check_ratio, check_tensors


def test_pspace_ekfac_vs_kfac():
    """
    Check that EKFAC matrix is closer to block diag one in the
    sense of the Frobenius norm
    """
    eps = 1e-5
    for get_task in [get_fullyconnect_task, get_convnet_task]:
        train_loader, net, loss_function = get_task()

        m2_generator = M2Gradients(model=net,
                                   dataloader=train_loader,
                                   loss_function=loss_function)

        M_kfac = KFACMatrix(m2_generator)
        M_ekfac = EKFACMatrix(m2_generator)
        M_blockdiag = BlockDiagMatrix(m2_generator)

        # here KFAC and EKFAC should be the same
        for split in [True, False]:
            diff = M_kfac.get_matrix(split_weight_bias=split) - \
                M_ekfac.get_matrix(split_weight_bias=split)
            assert torch.norm(diff) < eps

        # now we compute the exact diagonal:
        M_ekfac.update_diag()
        assert torch.norm(M_kfac.get_matrix() - M_blockdiag.get_matrix()) > \
            torch.norm(M_ekfac.get_matrix() - M_blockdiag.get_matrix())


def test_pspace_ekfac_vs_direct():
    """
    Check EKFAC basis operations against direct computation using
    get_matrix
    """
    for get_task in [get_fullyconnect_task, get_convnet_task]:
        train_loader, net, loss_function = get_task()

        m2_generator = M2Gradients(model=net,
                                   dataloader=train_loader,
                                   loss_function=loss_function)

        M_ekfac = EKFACMatrix(m2_generator)
        v = random_pvector(net)

        # the second time we will have called update_diag
        for i in range(2):
            vTMv_direct = torch.dot(torch.mv(M_ekfac.get_matrix(),
                                             v.get_flat_representation()),
                                    v.get_flat_representation())
            vTMv_ekfac = M_ekfac.vTMv(v)
            check_ratio(vTMv_direct, vTMv_ekfac)

            trace_ekfac = M_ekfac.trace()
            trace_direct = torch.trace(M_ekfac.get_matrix())
            check_ratio(trace_direct, trace_ekfac)

            frob_ekfac = M_ekfac.frobenius_norm()
            frob_direct = torch.norm(M_ekfac.get_matrix())
            check_ratio(frob_direct, frob_ekfac)

            mv_direct = torch.mv(M_ekfac.get_matrix(),
                                 v.get_flat_representation())
            mv_ekfac = M_ekfac.mv(v)
            check_tensors(mv_direct, mv_ekfac.get_flat_representation())

            M_ekfac.update_diag()