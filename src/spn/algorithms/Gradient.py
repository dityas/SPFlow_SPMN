from spn.structure.Base import eval_spn_top_down, Sum, Product, Leaf, get_number_of_nodes, get_nodes_by_type
from spn.algorithms.Inference import log_likelihood
from spn.algorithms.Marginalization import marginalize
import numpy as np
import collections


_node_gradient = {}



def gradient_backward(spn, lls_per_node):
    node_gradients = {}
    node_gradients[Sum] = sum_gradient_backward
    node_gradients[Product] = prod_gradient_backward
    node_gradients[Leaf] = leaf_gradient_backward

    gradient_result = np.zeros_like(lls_per_node)

    eval_spn_top_down(
        spn,
        node_gradients,
        parent_result=np.zeros((lls_per_node.shape[0])),
        gradient_result=gradient_result,
        lls_per_node=lls_per_node,
    )

    return gradient_result


def leaf_gradient_backward(node, parent_result, gradient_result=None, lls_per_node=None):
    gradients = np.zeros((parent_result.shape[0]))
    gradients[:] = parent_result  # log_sum_exp

    gradient_result[:, node.id] = gradients


def sum_gradient_backward(node, parent_result, gradient_result=None, lls_per_node=None):
    gradients = np.zeros((parent_result.shape[0]))
    gradients[:] = parent_result  # log_sum_exp

    gradient_result[:, node.id] = gradients

    messages_to_children = []

    for i, c in enumerate(node.children):
        messages_to_children.append(gradients + np.log(node.weights[i]))

    assert not np.any(np.isnan(messages_to_children)), "Nans found in iteration"

    return messages_to_children


def prod_gradient_backward(node, parent_result, gradient_result=None, lls_per_node=None):
    gradients = np.zeros((parent_result.shape[0]))
    gradients[:] = parent_result  # log_sum_exp

    gradient_result[:, node.id] = gradients

    messages_to_children = []

    # TODO handle zeros for efficiency, darwiche 2003
    output_ll = lls_per_node[:, node.id]

    for i, c in enumerate(node.children):
        messages_to_children.append(output_ll - lls_per_node[:, c.id])

    assert not np.any(np.isnan(messages_to_children)), "Nans found in iteration"

    return messages_to_children


def add_node_gradient(node_type, lambda_func):
    _node_gradient[node_type] = lambda_func


def feature_gradient(node, data, node_gradient_functions=_node_gradient, lls_per_node=None):
    '''
    Feature gradients are computed for the input query and each feature using
    the backwards automatic differentiation. In mathematicl terms, it computes the
    partial derivatives \partial P(X) / \partial X_i
 

    :param node: Node for the gradient calculation
    :param data: data for the computation. NaN values are implicitely marginalized out
    :param gradients_results: optional for storing the intermediate gradients
    :param lls_per_node: optional for storing the intermediate results
    '''

    all_leaves = get_nodes_by_type(node, Leaf)

    if not lls_per_node:
        lls_per_node = np.full((data.shape[0], get_number_of_nodes(node)), np.nan)
    lls = log_likelihood(node, data, lls_matrix=lls_per_node)

    gradients = np.exp(gradient_backward(node, lls_per_node))

    node_gradients = []

    for spn_node in all_leaves:
        i = spn_node.id
        result = node_gradient_functions[type(spn_node)](spn_node, data)
        node_gradients.append(result * gradients[:, i].reshape(-1,1))

    node_gradients = np.array(node_gradients)

    return np.nansum(node_gradients, axis=0)
