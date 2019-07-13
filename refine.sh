#!/bin/bash

FILES=./clips/*
for input_file in $FILES; do
    f=$(basename $input_file)
    output_file="./refined_clips/${f}"
    echo "Processing $f"
    ffmpeg -i $input_file -pix_fmt yuv420p -y -crf 18 $output_file
done

