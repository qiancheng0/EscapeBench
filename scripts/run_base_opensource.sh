cd src

python agent_base.py \
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

# Game Choices: game1-1 game1-2 game1-3 game1-4 game1-5 game2-5 game3-1 game3-2 game1-1-easy game1-2-easy game1-3-easy game1-4-easy game1-5-easy game2-5-easy game3-1-easy game3-2-easy game1-1-hard game1-2-hard game1-3-hard game1-4-hard game1-5-hard game2-5-hard game3-1-hard game3-2-hard game2-1 game2-2 game2-3 game2-4 game2-1-easy game2-2-easy game2-3-easy game2-4-easy game2-1-hard game2-2-hard game2-3-hard game2-4-hard