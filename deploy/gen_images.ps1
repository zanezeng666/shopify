param([string]$Mode = "wide")
$script = "c:\Users\admin\AppData\Local\Programs\CodeBuddy CN\resources\app\extensions\genie\out\extension\builtin\buddy-multimodal-generation\scripts\buddy-cloud.py"
$tok = Get-Content "e:\worksapce\shopify\deploy\assets\.gcred" -Raw
$tok = $tok.Trim()
$dir = "e:\worksapce\shopify\deploy\assets"

if ($Mode -eq "wide") {
  $prompts = @{
    "gen1" = "Professional product photography of replacement battery packs for medical devices, sleek black and grey battery modules with subtle blue charge indicator lights, arranged on a clean white laboratory surface, soft studio lighting, high-end e-commerce marketing style, photorealistic, no text, wide horizontal composition"
    "gen2" = "Close-up photography of a gloved technician hands installing a replacement battery module into a patient monitor in a modern bright hospital, shallow depth of field, cool clinical color palette with blue accents, photorealistic advertising photography, no text, wide horizontal composition"
  }
} else {
  $prompts = @{
    "gen3" = "Vertical composition, premium medical device replacement battery packs neatly stacked and floating at slight angles on a soft gradient light-blue studio background, dramatic rim lighting, glossy professional e-commerce hero image, photorealistic, no text"
    "gen4" = "Vertical composition, a defibrillator and patient monitor in a bright modern hospital room, fresh replacement battery packs in the foreground on a clean table, shallow depth of field, clean professional medical aesthetic, photorealistic advertising photo, no text"
  }
}

foreach ($k in $prompts.Keys) {
  Write-Host "--- generating $k ---"
  python $script image $prompts[$k] --token $tok --max-poll-time 240 2>$null | Out-File "$dir\$k.json" -Encoding utf8
  Get-Content "$dir\$k.json" | Select-Object -Last 4
}
