cd src

python agent_base.py \
    --is_api \
    --stuck_steps 50 \
    --models <API model name> \
    --games <games> \
    --max_steps 4000 \
    --memory 10 \
    --use_cot \
    --overwrite \
    --stuck_behavior help \
    --output_suffix <suffix mark>