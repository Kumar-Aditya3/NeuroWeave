from __future__ import annotations

import os
from pathlib import Path

import torch
from diffusers import StableDiffusionXLPipeline


class DiffusionGenerator:
    """Local GPU-based diffusion image generation with deterministic seeding and quality-first defaults."""

    _instance = None
    _pipeline = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.device = self._select_device()
        self.model_id = os.getenv("DIFFUSION_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
        self.pipeline = None
        self.timeout_seconds = int(os.getenv("DIFFUSION_TIMEOUT_SECONDS", "40"))
        self.num_inference_steps = int(os.getenv("DIFFUSION_STEPS", "30"))
        self.guidance_scale = float(os.getenv("DIFFUSION_GUIDANCE_SCALE", "7.5"))

    def _select_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def warm_up(self) -> None:
        """Load model into memory on first call."""
        if self.pipeline is not None:
            return
        try:
            self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            self.pipeline = self.pipeline.to(self.device)
            if self.device == "cuda":
                self.pipeline.enable_attention_slicing()
        except Exception as e:
            raise RuntimeError(f"Failed to load diffusion model {self.model_id}: {e}")

    def generate(
        self,
        prompt: str,
        seed: int,
        width: int = 1920,
        height: int = 1080,
    ) -> tuple[object, dict]:
        """Generate image via diffusion and return PIL image + metadata."""
        if self.pipeline is None:
            self.warm_up()

        # Ensure seed is valid for torch
        seed_int = int(seed) % (2**32)
        generator = torch.Generator(device=self.device).manual_seed(seed_int)

        try:
            image = self.pipeline(
                prompt=prompt,
                height=height,
                width=width,
                num_inference_steps=self.num_inference_steps,
                guidance_scale=self.guidance_scale,
                generator=generator,
            ).images[0]

            metadata = {
                "model": self.model_id,
                "device": self.device,
                "steps": self.num_inference_steps,
                "guidance_scale": self.guidance_scale,
                "seed": seed_int,
                "width": width,
                "height": height,
            }
            return image, metadata
        except Exception as e:
            raise RuntimeError(f"Diffusion generation failed: {e}")


def get_generator() -> DiffusionGenerator:
    """Singleton accessor for diffusion generator."""
    return DiffusionGenerator()
