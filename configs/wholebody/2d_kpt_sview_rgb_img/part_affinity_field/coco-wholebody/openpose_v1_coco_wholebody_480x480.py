log_level = 'INFO'
load_from = None
resume_from = None
dist_params = dict(backend='nccl')
workflow = [('train', 1)]
checkpoint_config = dict(interval=50)
evaluation = dict(interval=50, metric='mAP', key_indicator='AP')

optimizer = dict(
    type='Adam',
    lr=0.0015,
)
optimizer_config = dict(grad_clip=None)
# learning policy
lr_config = dict(
    policy='step',
    warmup='linear',
    warmup_iters=500,
    warmup_ratio=0.001,
    step=[200, 260])
total_epochs = 300
log_config = dict(
    interval=50,
    hooks=[
        dict(type='TextLoggerHook'),
        # dict(type='TensorboardLoggerHook')
    ])

channel_cfg = dict(
    dataset_joints=133,
    dataset_channel=[
        list(range(133)),
    ],
    inference_channel=list(range(133)))

data_cfg = dict(
    image_size=480,
    base_size=256,
    base_sigma=2,
    heatmap_size=[60],
    num_joints=channel_cfg['dataset_joints'],
    dataset_channel=channel_cfg['dataset_channel'],
    inference_channel=channel_cfg['inference_channel'],
    num_scales=1,
    scale_aware_sigma=False,
    with_bg=False)

# model settings
model = dict(
    type='PartAffinityField',
    pretrained='mmcls://vgg16_bn',
    backbone=dict(
        type='OpenPoseNetworkV1',
        in_channels=3,
        out_channels_cm=133,
        out_channels_paf=270,
        stem_feat_channels=128,
        num_stages=6),
    keypoint_head=dict(
        type='PAFHead',
        heatmap_heads_cfg=[
            dict(
                type='DeconvHead',
                num_deconv_layers=0,
                extra=dict(final_conv_kernel=0),
                loss_keypoint=dict(type='MaskedMSELoss', )),
        ] * 6,
        paf_heads_cfg=[
            dict(
                type='DeconvHead',
                num_deconv_layers=0,
                extra=dict(final_conv_kernel=0),
                loss_keypoint=dict(type='MaskedMSELoss', )),
        ] * 6,
        heatmap_index=[0, 1, 2, 3, 4, 5],
        paf_index=[6, 7, 8, 9, 10, 11],
    ),
    train_cfg=dict(),
    test_cfg=dict(
        num_joints=channel_cfg['dataset_joints'],
        max_num_people=30,
        scale_factor=[0.5, 1, 1.5, 2, 2.5],
        with_heatmaps=[True],
        with_pafs=[True],
        project2image=True,
        align_corners=False,
        nms_kernel=5,
        nms_padding=2,
        tag_per_joint=True,
        detection_threshold=0.1,
        tag_threshold=1,
        use_detection_val=True,
        ignore_too_much=False,
        adjust=True,
        refine=True,
        flip_test=True,
        with_bg=data_cfg['with_bg']))

train_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(
        type='BottomUpRandomAffine',
        rot_factor=30,
        scale_factor=[0.75, 1.5],
        scale_type='short',
        trans_factor=40),
    dict(type='BottomUpRandomFlip', flip_prob=0.5),
    dict(type='ToTensor'),
    dict(
        type='NormalizeTensor',
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]),
    dict(
        type='MultitaskGatherTarget',
        pipeline_list=[
            [
                dict(
                    type='BottomUpGenerateHeatmapTarget',
                    sigma=2,
                    with_bg=data_cfg['with_bg'])
            ],
            [dict(
                type='BottomUpGeneratePAFTarget',
                limb_width=1,
            )],
        ],
        pipeline_indices=[0] * 6 + [1] * 6,
        keys=['targets', 'masks']),
    dict(type='Collect', keys=['img', 'targets', 'masks'], meta_keys=[]),
]

val_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='BottomUpGetImgSize', test_scale_factor=[0.5, 1, 1.5, 2, 2.5]),
    dict(
        type='BottomUpResizeAlign',
        transforms=[
            dict(type='ToTensor'),
            dict(
                type='NormalizeTensor',
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]),
        ]),
    dict(
        type='Collect',
        keys=['img'],
        meta_keys=[
            'image_file', 'aug_data', 'test_scale_factor', 'base_size',
            'center', 'scale', 'flip_index', 'skeleton'
        ]),
]

test_pipeline = val_pipeline

data_root = 'data/coco'
data = dict(
    samples_per_gpu=24,
    workers_per_gpu=2,
    train=dict(
        type='BottomUpCocoWholeBodyDataset',
        ann_file=f'{data_root}/annotations/coco_wholebody_train_v1.0.json',
        img_prefix=f'{data_root}/train2017/',
        data_cfg=data_cfg,
        pipeline=train_pipeline),
    val=dict(
        type='BottomUpCocoWholeBodyDataset',
        ann_file=f'{data_root}/annotations/coco_wholebody_val_v1.0.json',
        img_prefix=f'{data_root}/val2017/',
        data_cfg=data_cfg,
        pipeline=val_pipeline),
    test=dict(
        type='BottomUpCocoWholeBodyDataset',
        ann_file=f'{data_root}/annotations/coco_wholebody_val_v1.0.json',
        img_prefix=f'{data_root}/val2017/',
        data_cfg=data_cfg,
        pipeline=val_pipeline),
)
