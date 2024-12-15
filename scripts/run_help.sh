cd src

python agent_creative.py \
    --stuck_steps 0 \
    --models test \
    --port 00000 \
    --games game1-1 \
    --max_steps 200 \
    --memory 0 \
    --use_cot \
    --overwrite \
    --stuck_behavior help \
    --output_suffix test_help