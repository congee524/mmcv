import pytest
import torch

from mmcv.cnn.bricks.transformer import (FFN, BaseTransformerLayer,
                                         MultiheadAttention,
                                         TransformerLayerSequence)


def test_multiheadattention():
    batch_dim = 2
    embed_dim = 5
    num_query = 100
    attn_batch_first = MultiheadAttention(
        embed_dims=5,
        num_heads=5,
        attn_drop=0,
        proj_drop=0,
        dropout_layer=dict(type='DropPath', drop_prob=0.),
        batch_first=True)

    attn_query_first = MultiheadAttention(
        embed_dims=5,
        num_heads=5,
        attn_drop=0,
        proj_drop=0,
        dropout_layer=dict(type='DropPath', drop_prob=0.),
        batch_first=False)

    param_dict = dict(attn_query_first.named_parameters())
    for n, v in attn_batch_first.named_parameters():
        param_dict[n].data = v.data

    input_batch_first = torch.rand(batch_dim, num_query, embed_dim)
    input_query_first = input_batch_first.transpose(0, 1)

    assert attn_query_first(input_query_first).sum() == attn_batch_first(
        input_batch_first).sum()

    key_batch_first = torch.rand(batch_dim, num_query, embed_dim)
    key_query_first = key_batch_first.transpose(0, 1)

    assert attn_query_first(input_query_first,
                            key_query_first).sum() == attn_batch_first(
                                input_batch_first, key_batch_first).sum()

    residue = torch.ones_like(input_query_first)

    assert torch.allclose(
        attn_query_first(input_query_first, key_query_first,
                         residual=residue).sum(),
        attn_batch_first(input_batch_first, key_batch_first).sum() +
        residue.sum() - input_batch_first.sum())


def test_ffn():
    with pytest.raises(AssertionError):
        FFN(num_fcs=1)
    ffn = FFN(dropout=0)
    input_tensor = torch.rand(2, 20, 256)
    input_tensor_nbc = input_tensor.transpose(0, 1)
    assert ffn(input_tensor).sum() == ffn(input_tensor_nbc).sum()
    residue = torch.rand_like(input_tensor)
    torch.allclose(
        ffn(input_tensor, residue).sum(),
        ffn(input_tensor).sum() + residue.sum() - input_tensor.sum())


def test_basetransformerlayer():
    attn_cfgs = dict(type='MultiheadAttention', embed_dims=256, num_heads=8),
    feedforward_channels = 2048
    ffn_dropout = 0.1
    operation_order = ('self_attn', 'norm', 'ffn', 'norm')

    # test deprecated_args
    baselayer = BaseTransformerLayer(
        attn_cfgs=attn_cfgs,
        feedforward_channels=feedforward_channels,
        ffn_dropout=ffn_dropout,
        operation_order=operation_order)
    assert baselayer.batch_first is False
    assert baselayer.ffns[0].feedforward_channels == feedforward_channels

    attn_cfgs = dict(type='MultiheadAttention', num_heads=8, embed_dims=256),
    feedforward_channels = 2048
    ffn_dropout = 0.1
    operation_order = ('self_attn', 'norm', 'ffn', 'norm')
    baselayer = BaseTransformerLayer(
        attn_cfgs=attn_cfgs,
        feedforward_channels=feedforward_channels,
        ffn_dropout=ffn_dropout,
        operation_order=operation_order,
        batch_first=True)
    assert baselayer.attentions[0].batch_first


def test_transformerlayersequence():
    squeue = TransformerLayerSequence(
        num_layers=6,
        transformerlayers=dict(
            type='BaseTransformerLayer',
            attn_cfgs=[
                dict(
                    type='MultiheadAttention',
                    embed_dims=256,
                    num_heads=8,
                    dropout=0.1),
                dict(type='MultiheadAttention', embed_dims=256, num_heads=4)
            ],
            feedforward_channels=1024,
            ffn_dropout=0.1,
            operation_order=('self_attn', 'norm', 'cross_attn', 'norm', 'ffn',
                             'norm')))
    assert len(squeue.layers) == 6
    assert squeue.pre_norm is False
    with pytest.raises(AssertionError):
        TransformerLayerSequence(
            num_layers=6,
            transformerlayers=[
                dict(
                    type='BaseTransformerLayer',
                    attn_cfgs=[
                        dict(
                            type='MultiheadAttention',
                            embed_dims=256,
                            num_heads=8,
                            dropout=0.1),
                        dict(type='MultiheadAttention', embed_dims=256)
                    ],
                    feedforward_channels=1024,
                    ffn_dropout=0.1,
                    operation_order=('self_attn', 'norm', 'cross_attn', 'norm',
                                     'ffn', 'norm'))
            ])
