# ArchaeoAI public research demo

This dependency-free static site presents coordinate-safe, verified ArchaeoAI research evidence.
It contains no candidate locations, private terrain, private score tables, or review images.

## Preview locally

From the repository root:

```powershell
python -m http.server 8000
```

Then open `http://127.0.0.1:8000/website/`.

## Future deployment

- **Vercel:** set the project root directory to `website`; no build command is required.
- **GitHub Pages:** publish `website` as the Pages artifact through an approved Pages workflow.

No deployment workflow is included or enabled yet. The anticipated canonical URL and social-image
metadata in `index.html` should be confirmed when the final hosting destination is chosen.

## Research boundary

All displayed results are aggregate and traceable to frozen repository evidence. The generated
contour texture is explicitly synthetic and depicts no real place. Model scores are not
archaeological probabilities, and the site makes no discovery claim.
