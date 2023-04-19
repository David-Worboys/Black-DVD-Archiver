#!/bin/bash

# Set input and output directories
input_dir="./icons_old"
output_dir="./icons"

# Create output directory if it doesn't exist
if [ ! -d "$output_dir" ]; then
  mkdir -p "$output_dir"
fi

# Loop through PNG files in input directory and trim them
for file in "$input_dir"/*.png; do
  filename=$(basename -- "$file")
  output_file="$output_dir/${filename%.*}.png"
  ./tools/magick "$file" -resize 50% "$output_file"
done

