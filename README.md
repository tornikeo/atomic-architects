# Atomic Architect

> [!NOTE]
> See [main.ipynb](./main.ipynb) for the implementation (the notebook is the actual executable) 

This is a comptuer vision tracking tool for nano-flakes that is very lightweight and doesn't involve any AI models. Here's how it works:

![](https://github.com/tornikeo/cdn/raw/master/assets/atomic_arch/image-1.png)

The camera starts by looking through a plastic sheet that has a flake attached to it. The sheet is transparent and out of focus, so it is very blurry initially. The plastic sheet is then lowered to the substrate and it then becomes visible. This step looks like this:

![](https://github.com/tornikeo/cdn/raw/master/assets/atomic_arch/image-2.png)

At this point, the flake sticks to the substrate and stays there. The sheet is gently peeled off, leaving the flake in place. This looks like so:

![](https://github.com/tornikeo/cdn/raw/master/assets/atomic_arch/image-3.png)

You can also read more about this process in [this paper](https://arxiv.org/pdf/1311.4829.pdf). To actually make something useful, you will need to repeat this flake transfer multiple times and build really complex, tiny structures. The unfortunate hard part is that all of this is a really slow, manual process that requires a lot of patience. 

## The solution

The solution is to automatically track the flakes from the camera feed and use that data to automatically guide a robotic arm to assemble a structure. You could then leave the assembly robot overnight and come back to complete structures. 

One (unworkable) approach is to try fine-tuning an AI model, like [YOLO](https://en.wikipedia.org/wiki/You_Only_Look_Once), to detect the flake for you. This didn't work because we only had 3 really short videos of the above transfer process. 

Because we don't have enough data, we are left in the 'classical' mode of computer vision: frame-differencing, edge detection, et al. So, the algorithm we develop looks like this:

```py
video = open('video.mp4')
# Extract frame as a `numpy` array from video feed, using `pyav`
background = blur(rolling_ball(video[0]))

for idx, frame in enumerate(video)[::3]: # every 3rd frame only
  frame = togray(down(frame)) - background # Downsample, grayscale and subtract background. 
  edges = binarydilate(canny(frame)) # detect edges and dilate to connect edge breaks. 
  blobs = fill_holes(watershed(edges)) # Fill holes to make blobs
  labels = labels(blobs) # Separate blobs get separate IDs
```

This is the basic layout of the code. However, as the plastic sheet touches the substrate, the background changes—it becomes lighter. When that happens, we simply invalidate and recalculate the background. 

This is the core of the algorithm that allows us to track the nanoflakes with really good precision and virtually no data, as shown below:

![](https://github.com/tornikeo/cdn/raw/master/assets/atomic_arch/aa-processed-compressed.webm)

## Install and run

```bash
./run.sh --input_video store/all_videos/000000.mp4 --output_dir store/results/000000
```

See the output files at `store/results/000000`.

## Introduction

Assumptions
- Marker must be **fully** visible.
- Assume not too much jitter and deviation. 
- All things of interest have reasonably well-defined edges.

Core Deliverables:
- [x] PVC tracking
- [x] Closest and middle crystal distances to PVC
- [x] Coverage
- [x] Crystal tracking

Additional features:
- [x] CLI crystal size filter has to be in square microns
- [x] Crystal and PVC tracking are separated and thus more accurate
- [x] PVC tracking auto-adjusts BG model when light shifted.
- [x] Visualize: distances and coverage. Optimize up generation speed.
- [x] Major speed increase due to new approach for PVC tracking
- [x] New manually labelled dataset for several videos
- [x] Warnings: Missing marker, marker overlapping with a large crystal, background lighting change, etc.
- [x] Main loop image prefetching (separate thread readies new image before the loop has the time to request new one)

Optimizations:
- [x] Parallelized visualization loop
- [x] Separate thread for image prefetching
- [x] Downsampled canny edge detection, since Canny routine is extremely slow
- [x] Performance tracker with `CatchTime`

## Algorithm overview

### Crystal detection routine:
#### Pseudocode
```python
for frame in video:
    edges = canny_edge_detector(frame)
    edges = stitch_holes_in_edges(edges)
    crystal_candidates = fill_all_closed_edges(edges)
    detected_crystals = remove_small_objects(crystal_candidates)
    detected_crystals = remove_thin_objects(detected_crystals)
```
#### Crystal Memorization
Crystal segmentation follows the above loop closely, however, during the development it became apparent that the screen was too unstable (shaky) 
to just display predictions based on the last frame only.
To remedy this instability, and to also include the additional information (that is, the **assumption that crystals don't move around too much once they are in sight**) 
we developed a temporal-averaging approach. In the above loop, we add the following few lines of code:
```python
crystal_memory = all_zeros()
for frame in video:
    ...
    detected_crystals = ... # Same as above
    if not polymer_is_in_contact:
        update(crystal_memory, detected_crystals, alpha)
```
where the `update` function is a per-pixel running average function, defined as:

```python
    crystal_memory = crystal_memory * alpha + (1 - alpha) * detected_crystals
```
with `alpha` being a number close to 1.0. Specifically, when polymer is in contact, the alpha is 0.995, and 0.95 otherwise. Higher alpha means memory
is more frozen, and less updated. This is necessary because having polymer in view disrupts `canny_edge_detector`. 

Lastly, the predicted and displayed crystals are created using the following code:

```python
    for frame in video:
        ...
        crystal_memory = ...
        predicted_crystals = get_high_confidence_segments(crystal_memory)
        predicted_crystals = filter( predicted_crystals, crystal_doesnt_touch_edge )
        predicted_crystals = filter( predicted_crystals, crystal_doesnt_touch_marker )
```


### PVC contact area detection routine:
#### Pseudocode

```python
background = rolling_ball(first_frame)
for frame in video:
    frame_foreground = remove_background(frame, background)
    if pixel_intensity(frame_foreground) > threshold:
        contact_area_candidates = remove_small_and_medium_size_objects(frame_foreground)
        contact_area_candidates = stitch_small_holes(contact_area_candidates)
        non_contact_area = get_largest_non_contact_area(contact_area_candidates)
        pvc_contour_line = get_line_between(contact_area, non_contact_area)
```

#### PVC contour tracking
Contour tracking was posed a challenge on the opposite end of the CV spectrum - contour is expected to move around rapidly, and it is not 
localized in any single cell of the screen. It could also be composed of multiple segments. 

We address these issues by predicting the background model of the starting frame, using the `rolling_ball` algorithm on the grayscale frame, and using that to
create a foreground-only image. **It is important to note that `rolling_ball` assumes the foreground objects will be brighter on average**. If this assumption is 
violated, the contour tracker might fail to function.

Once we have the foreground-only image, we detect the potential contact areas by thresholding - the contact area is always brighter, because of the changed optical properties of the substrate-polymer "sandwich".
The result of the thresholding is then post-processed to stitch unwanted holes and to separate out non-contact area from the available the rest of the image.

Finally, we calculate the PVC contour from the line separating the contact and non-contact areas.

In several videos, the background shows spurious lighting changes, causing the `pixel_intensities` function to cross the `threshold` and causing an error. This has been remedied by the following additional check:

```python
if pixel_intensity(frame_foreground) > threshold:
    if number_of_small_disjointed_segments(frame_foreground) > 500:
        print_warning("background shift detected!")
        background = rolling_ball(frame) # Update background model
        frame_foreground = remove_background(frame, background)
```

Note that unlike crystal segmentation, PVC contour tracking is fully dependent on the current frame, and has no memory. It is also fully decoupled from crystal segmentation, making it more robust to errors.

### Marker detection
#### Pseudocode

```python
frame = get_first_frame_from_video(video)
edges = canny_edge_detector(frame)
edges = stitch_holes_in_edges(edges)
marker_candidates = fill_all_closed_edges(edges)
marker_candidates = remove_objects_too_small_or_large(marker_candidates)
marker = find_candidate_with_90_deg_rotational_symmetry(marker_candidates)
marker_symbols = find_segments_that_are_very_close_to_marker(edges, marker)
marker_symbols = filter_out_objects_that_are_of_symbol_like_size(marker_symbols)
```

#### Reliable marker location and orientation
Initially, the marker detection was handled using `rotation_invariant_template_matching` approach, which proved to be unreliable, given that markers in videos are shown in various 
slighly differing shades and sizes, not only different rotations. 

The current approach exploits the *rotational symmetry* of the marker - which is a cross, a shape which is invariant under 90 degree rotational transform, in particular, the pseudocode for detecting the marker is:

```python
marker_candidate = ...

for angle in [0, 90, 180, 270]:
    cardinal_similarities = dot_product_similarity(marker_candidate, rotate(marker_candidate, angle))

for angle in [45, 135, 225, 315]:
    sub_cardinal_similarities = dot_product_similarity(marker_candidate, rotate(marker_candidate, angle)) # Make sure square-like objects don't pass
    
if min(cardinal_similarities) > 2 * sub_cardinal_similarities:
    # marker_candidate is actually a marker!
```

Next, we need to find the correct upright orientation of the marker. This is done by rotating the marker around in 1 degree increments, and calculating its bounding box area. We know the 
area will be maximal when the marker is in upright position.

Finally, we need to find symbol (each have been detected as a segment, placed near the marker itself). In order to do this, we look for objects within a narrow size range, that intersect with
the marker's bounding box. These objects are later sent to `custom_ocr` function, as discussed in the next section.

### Symbol prediction
#### Pseudocode
```python
for marker_symbol in marker_symbols:
    font_symbol_similarities = []
    for symbol in all_font_files:
        font_symbol_similarities.append(dot_product_similarity(marker_symbol, symbol))
    similarities = average_similarity_per_symbol( font_symbol_similarities )
    if is_in_first_place(marker_symbol):
        predicted_symbol = argmax( filter( similarities, only_uppercase_latin_symbols ) )
    else:
        predicted_symbol = argmax( filter( similarities, only_digits ) )
```

#### Dot product based OCR

In order to perform OCR, we list all font files under `store/fonts`, and load them in the memory as black-and-white images. For each symbol candidate, we calculate dot-product similarity with every symbol from each font. 
Highest font symbols with highest similarity are then as prediction candidates. We employ our knowledge that the first symbol has to be a latin uppercase character, and the rest a digit, by filtering out respective candidates to match this assumption. **It is important to note that if the edge of any character intersects with the border or a crystal in a frame, the character will not be identified in that frame**. 


### Other Caveats and tips

In order to accelerate frame processing speed, segmentation and contour data is **downscaled by a factor of 4 when saved**. This includes, for example, crystal segmentation data, marker bounding boxes, etc.. It is thus important to upscale these results when reading from the JSON. All the necessary scaling is done in the `visualization` section after loading, which should be used as a guide to programmically correctly interpreting the results in the JSON. 

To increase OCR accuracy, add or remove `.tff` font files from `store/fonts`. The closer the added font is to the font used in creating marker symbols the higher the accuracy will be (Note for example, the curious shape of uppercase "N" in one of the videos, right now it is interpeted as "H", since the font files we found do not have that particular shape). Also, the hershey fonts don't seem to be the right fit, given the shape of "N" doesn't match.

To increase performance, crystal-center-to-PVC-distances are not being calculated. These can be enabled by uncommenting several marked lines in `get_stable_segments` function. Further, use `CatchTime.plot()` functionality to see which segments take most time during a run.

Once a run is finished, the resulting notebook can be seen as a `results.html` file. It can be opened by dropping it directly onto the browser tab.

If a video is not being fully processed for some reason **and** no exceptions are being thrown, try cleaning ffmpeg cache using `--clean_ffmpeg_cache=True` argument.

### Bonus
It is possible to interactively run the `main.ipynb` notebook by following an [online guide](https://jupyter-docker-stacks.readthedocs.io/en/latest/using/running.html) or by `pip install`-ing the `jupyterlab` package.

