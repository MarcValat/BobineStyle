# -*- coding: utf-8 -*-
"""
Created on Sat Jul 13 23:10:18 2024

VERSION EN TEST : Le scale n'est plus fait car les PlayRes ne sont plus définis et sont scale
automatiquement par le lecteur (VLC fonctionne pour Nier Automata)

"""

import os
import subprocess
import json
import pysubs2
from tkinter import Tk
from tkinter.filedialog import askdirectory
import concurrent.futures

def extract_subtitles(mkv_file, output_subtitles_dir):
    base_name = os.path.basename(mkv_file)
    mkv_logs = [f"\n--- Processing MKV file: {base_name} ---"]
    
    mkvextract_path = r"C:\Program Files\MKVToolNix\mkvextract.exe"
    output_subtitles_dir = os.path.abspath(output_subtitles_dir)
    mkvmerge_path = r"C:\Program Files\MKVToolNix\mkvmerge.exe"
    mkvmerge_output = subprocess.check_output([mkvmerge_path, "-J", mkv_file])
    tracks_info = json.loads(mkvmerge_output)

    mkv_base_name = os.path.splitext(base_name)[0]
    extracted_subtitle_tracks = []

    for track in tracks_info["tracks"]:
        track_number = track["id"]
        if track["type"] == "subtitles" and track["properties"]["language"] in ["fre", "und"]:
            track_name = track["properties"].get("track_name", f"subtitle_track_{track_number}")
            output_file = os.path.join(output_subtitles_dir, f"{mkv_base_name}_{track_name}.ass")
            subprocess.run([mkvextract_path, "tracks", mkv_file, f"{track_number}:{output_file}"], check=True)
            
            # Process subtitle file and print `.ass` specific logs
            ass_logs = change_style_in_file(output_file, mkv_file)
            print("\n".join(ass_logs))
            
            mkv_logs.append(f"Subtitle extracted and styled: {os.path.basename(output_file)}")
            extracted_subtitle_tracks.append(output_file)

    return extracted_subtitle_tracks, mkv_logs

def calculate_style_properties(base_properties, base_resolution, target_resolution):
    """
    Calculate style properties dynamically based on resolution scaling.
    
    Args:
        base_properties (dict): The style properties for the base resolution (e.g., 1080p).
        base_resolution (tuple): The base resolution, e.g., (1920, 1080).
        target_resolution (tuple): The target resolution, e.g., (1280, 720).
    
    Returns:
        dict: The dynamically calculated style properties for the target resolution.
    """
    base_width, base_height = base_resolution
    target_width, target_height = target_resolution

    # Calculate scaling factors for width and height
    scaling_factor_x = target_width / base_width
    scaling_factor_y = target_height / base_height
    scaling_factor_font = (scaling_factor_x + scaling_factor_y) / 2

    # Calculate dynamic properties
    return {
        "fontsize": int(base_properties["fontsize"] / scaling_factor_font),
        "outline": base_properties["outline"] / scaling_factor_font,
        "shadow": base_properties["shadow"] / scaling_factor_font,
        "marginl": int(base_properties["marginl"] / scaling_factor_x),
        "marginr": int(base_properties["marginr"] / scaling_factor_x),
        "marginv": int(base_properties["marginv"] / scaling_factor_y),
    }

def create_dynamic_styles(original_resolution, base_resolution=(1920, 1080)):
    """Creates predefined styles dynamically based on resolution scaling."""
    # Parse original and base resolutions
    original_width, original_height = map(int, original_resolution.split('x'))
    base_width, base_height = base_resolution

    # Calculate scaling factors
    scaling_factor_x = base_width / original_width
    scaling_factor_y = base_height / original_height
    scaling_factor_font = (scaling_factor_x + scaling_factor_y) / 2

    # Define base properties for scaling
    base_properties = {
        "fontsize": 66,  # Default for 1080p
        "outline": 2.5,
        "shadow": 2.5,
        "marginl": 6,
        "marginr": 6,
        "marginv": 75,
    }

    # Dynamically calculate properties based on scaling factors
    scaled_properties = {
        "fontsize": int(base_properties["fontsize"] / scaling_factor_font),
        "outline": round(base_properties["outline"] / scaling_factor_font, 1),
        "shadow": round(base_properties["shadow"] / scaling_factor_font, 1),
        "marginl": int(base_properties["marginl"] / scaling_factor_x),
        "marginr": int(base_properties["marginr"] / scaling_factor_x),
        "marginv": int(base_properties["marginv"] / scaling_factor_y),
    }

    # Default style
    default_style = pysubs2.SSAStyle()
    default_style.fontname = "Trebuchet MS"
    default_style.fontsize = scaled_properties["fontsize"]
    default_style.primarycolor = pysubs2.Color(255, 255, 255, 0)
    default_style.secondarycolor = pysubs2.Color(255, 0, 0, 0)
    default_style.outlinecolor = pysubs2.Color(0, 0, 0, 0)
    default_style.shadowcolor = pysubs2.Color(0, 0, 0, 0)
    default_style.bold = True
    default_style.italic = False
    default_style.borderstyle = 1
    default_style.outline = scaled_properties["outline"]
    default_style.shadow = scaled_properties["shadow"]
    default_style.alignment = pysubs2.Alignment.BOTTOM_CENTER
    default_style.marginl = scaled_properties["marginl"]
    default_style.marginr = scaled_properties["marginr"]
    default_style.marginv = scaled_properties["marginv"]
    default_style.encoding = 1
    default_style.name = "Default"

    # Other styles derived from default
    default_top_style = default_style.copy()
    default_top_style.name = "DefaultTop"
    default_top_style.alignment = pysubs2.Alignment.TOP_CENTER

    defaultmargins_style = default_style.copy()
    defaultmargins_style.name = "Default - With margins"
    defaultmargins_style.marginl += 45
    defaultmargins_style.marginr += 45

    overlap_style = default_style.copy()
    overlap_style.name = "Overlap"
    overlap_style.primarycolor = pysubs2.Color(250, 238, 140)

    italic_top_style = default_top_style.copy()
    italic_top_style.name = "ItaliqueUP"
    italic_top_style.italic = True

    italic_style = default_style.copy()
    italic_style.name = "Italique"
    italic_style.italic = True

    tirets_default_style = default_style.copy()
    tirets_default_style.name = "TiretsDefault"
    tirets_default_style.alignment = pysubs2.Alignment.BOTTOM_LEFT
    tirets_default_style.marginl += 60

    tirets_italic_style = tirets_default_style.copy()
    tirets_italic_style.name = "TiretsItalique"
    tirets_italic_style.italic = True

    # Return all styles as a dictionary
    return {
        "Default": default_style,
        "Italique": italic_style,
        "Default I": italic_style,
        "TiretsDefault": tirets_default_style,
        "TiretsItalique": tirets_italic_style,
        "Default top": default_top_style,
        "DefaultUP": default_top_style,
        "DefaultTop": default_top_style,
        "ItaliqueUP": italic_top_style,
        "Default (Arial 1080p) - Copier": default_top_style,
        "Overlap": overlap_style,
        "Default - With margins": defaultmargins_style,
    }


def change_style_in_file(subtitle_file, mkv_file):
    logs = [f"\n--- Changing style for subtitle file: {os.path.basename(subtitle_file)} ---"]
    subs = pysubs2.load(subtitle_file)
    
    """
    # Set ScaleBorderAndShadow property
    subs.info["ScaledBorderAndShadow"] = "yes"
    logs.append("Enabled Scale border and shadow in subtitle properties.")
    """
    
    # Log the original script resolution
    original_play_res_x = int(subs.info.get("PlayResX", 1920))
    original_play_res_y = int(subs.info.get("PlayResY", 1080))
    logs.append(f"Original script resolution: {original_play_res_x}x{original_play_res_y}")

    # Do not modify PlayResX and PlayResY
    logs.append("Retaining original PlayResX and PlayResY values. No changes made.")

    # Apply predefined styles without scaling
    logs.append("Applying predefined styles without rescaling:")
    predefined_styles = create_dynamic_styles(f"{original_play_res_x}x{original_play_res_y}")
    for style_name, style in subs.styles.items():
        if style_name in predefined_styles:
            subs.styles[style_name] = predefined_styles[style_name]
            logs.append(f"  - Applied predefined style: {style_name}")
        else:
            logs.append(f"  - Skipped non-predefined style: {style_name}")

    # Save the updated subtitle file
    subs.save(subtitle_file)
    logs.append(f"Updated subtitle file saved: {subtitle_file}")
    return logs

def get_video_resolution(mkv_file):
    mkvmerge_path = r"C:\Program Files\MKVToolNix\mkvmerge.exe"
    result = subprocess.run([mkvmerge_path, '-J', mkv_file], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    for track in info['tracks']:
        if track["type"] == "video":
            return track["properties"]["pixel_dimensions"]
    print(f"Default resolution used for {mkv_file}")
    return "1920x1080"

def create_final_mkv_with_subtitles(input_file, output_file, subtitle_files, attachment_files):
    base_name = os.path.basename(input_file)
    print(f"Creating final MKV for: {base_name}")
    mkvmerge_path = r"C:\Program Files\MKVToolNix\mkvmerge.exe"
    sorted_subtitle_files = sorted(subtitle_files, key=os.path.getsize, reverse=True)
    largest_subtitle_file = sorted_subtitle_files[0]

    command = [mkvmerge_path, '-o', output_file, '--no-subtitles', '--title', '', input_file]

    # Ajouter les fichiers de sous-titres modifiés à la commande de fusion
    for subtitle_file in sorted_subtitle_files:
        if subtitle_file == largest_subtitle_file:
            track_name = "Français"
            default_track = "no"
            forced_track = "no"
        else:
            track_name = "Français (forcé)"
            default_track = "yes"
            forced_track = "yes"
        options = [
            "--language", "0:fre",
            "--track-name", f"0:{track_name}",
            "--default-track", f"0:{default_track}",
            "--forced-track", f"0:{forced_track}",
            subtitle_file
        ]
        command.extend(options)

    for attachment_file in attachment_files:
        command.extend(["--attach-file", attachment_file])

    subprocess.run(command, check=True)

def process_mkv_file(mkv_file, output_subtitles_dir, attachment_files, output_directory):
    extracted_subs, mkv_logs = extract_subtitles(mkv_file, output_subtitles_dir)
    
    if extracted_subs:
        create_final_mkv_with_subtitles(mkv_file, os.path.join(output_directory, f"{os.path.splitext(os.path.basename(mkv_file))[0]}.mkv"), extracted_subs, attachment_files)
    
    # Print the MKV processing logs after all subtitles have been processed
    print("\n".join(mkv_logs))

def process_all_mkv_files_in_directory(directory):
    mkv_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.mkv')]
    
    output_directory = os.path.join(directory, "Output")
    os.makedirs(output_directory, exist_ok=True)

    output_subtitles_dir = os.path.join(output_directory, "Sous-titres")
    os.makedirs(output_subtitles_dir, exist_ok=True)

    attachment_files = [
        r"C:\Users\Marc\Desktop\Dossiers\Logiciels\LogicielPourPlex\TrebuchetAttachments\trebuc_0.ttf",
        r"C:\Users\Marc\Desktop\Dossiers\Logiciels\LogicielPourPlex\TrebuchetAttachments\trebucbd_0.ttf",
        r"C:\Users\Marc\Desktop\Dossiers\Logiciels\LogicielPourPlex\TrebuchetAttachments\trebucbi_0.ttf",
        r"C:\Users\Marc\Desktop\Dossiers\Logiciels\LogicielPourPlex\TrebuchetAttachments\trebucit_0.ttf",
        r"C:\Users\Marc\Desktop\Dossiers\Logiciels\LogicielPourPlex\TrebuchetAttachments\arial_4.ttf"
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_mkv_file, mkv_file, output_subtitles_dir, attachment_files, output_directory)
            for mkv_file in mkv_files
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
                print("- Successfully processed file. -")
            except Exception as e:
                print(f"Error processing file: {e}")

if __name__ == "__main__":
    root = Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    directory = askdirectory(title="Choisir un dossier contenant des fichiers MKV")

    if directory:
        process_all_mkv_files_in_directory(directory)
    else:
        print("Aucun dossier sélectionné.")
