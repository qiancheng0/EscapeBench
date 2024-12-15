cd src

python agent_creative.py \
    --stuck_steps 50 \
    --models <model name> \
    --port 12345 \
    --games <games> \
    --max_steps 4000 \
    --memory 10 \
    --use_cot \
    --overwrite \
    --stuck_behavior help \
    --output_suffix <suffix mark>