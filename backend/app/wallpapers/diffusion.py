from __future__ import annotations

import os
import threading
from typing import Any

import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline


class DiffusionGenerator:
    """Local GPU-based diffusion image generation with deterministic seeding and quality-first defaults."""

    _instance = None
    _pipeline = None
    _generation_lock = threading.Lock()

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
        self.gpu_memory_gb = self._gpu_memory_gb()
        self.low_vram_mode = self.device == "cuda" and self.gpu_memory_gb is not None and self.gpu_memory_gb <= 4.5
        self.model_id = os.getenv("DIFFUSION_MODEL_ID", self._default_model_id())
        self.pipeline = None
        self.timeout_seconds = int(os.getenv("DIFFUSION_TIMEOUT_SECONDS", "40"))
        self.num_inference_steps = int(os.getenv("DIFFUSION_STEPS", self._default_steps()))
        self.guidance_scale = float(os.getenv("DIFFUSION_GUIDANCE_SCALE", "7.5"))
        self.height = int(os.getenv("DIFFUSION_HEIGHT", self._default_height()))
        self.width = int(os.getenv("DIFFUSION_WIDTH", self._default_width()))
        self.uses_cpu_offload = False

    def _gpu_memory_gb(self) -> float | None:
        if not torch.cuda.is_available():
            return None
        try:
            total_memory = torch.cuda.get_device_properties(0).total_memory
        except Exception:
            return None
        return round(total_memory / (1024**3), 2)

    def _default_model_id(self) -> str:
        if self.device == "cuda" and self.gpu_memory_gb and self.gpu_memory_gb < 6.0:
            return "runwayml/stable-diffusion-v1-5"
        return "stabilityai/stable-diffusion-xl-base-1.0"

    def _default_steps(self) -> str:
        if self.model_id == "runwayml/stable-diffusion-v1-5":
            return "18"
        return "30"

    def _default_width(self) -> str:
        if self.model_id == "runwayml/stable-diffusion-v1-5":
            return "1024"
        return "1344"

    def _default_height(self) -> str:
        if self.model_id == "runwayml/stable-diffusion-v1-5":
            return "576"
        return "768"

    def _pipeline_cls(self):
        if "stable-diffusion-xl" in self.model_id:
            return StableDiffusionXLPipeline
        return StableDiffusionPipeline

    def _pipeline_dtype(self) -> torch.dtype:
        return torch.float16 if self.device == "cuda" else torch.float32

    def _trim_prompt(self, prompt: str, max_words: int = 64) -> str:
        tokens = prompt.split()
        if len(tokens) <= max_words:
            return prompt
        return " ".join(tokens[:max_words])

    def _configure_pipeline(self, pipeline: Any) -> Any:
        self.uses_cpu_offload = False
        if self.device == "cuda":
            pipeline.enable_attention_slicing()
            if hasattr(pipeline, "enable_vae_slicing"):
                pipeline.enable_vae_slicing()
            if self.gpu_memory_gb and self.gpu_memory_gb <= 4.5 and hasattr(pipeline, "enable_model_cpu_offload"):
                pipeline.enable_model_cpu_offload()
                self.uses_cpu_offload = True
            else:
                pipeline = pipeline.to(self.device)
        else:
            pipeline = pipeline.to(self.device)
        return pipeline

    def _generator_device(self) -> str:
        # CPU offload pipelines coordinate execution across devices; the RNG generator
        # must stay on CPU to avoid cpu/cuda index_select mismatch in schedulers.
        if self.uses_cpu_offload:
            return "cpu"
        return self.device

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
            pipeline_cls = self._pipeline_cls()
            self.pipeline = pipeline_cls.from_pretrained(
                self.model_id,
                torch_dtype=self._pipeline_dtype(),
                use_safetensors=True,
            )
            self.pipeline = self._configure_pipeline(self.pipeline)
        except Exception as e:
            if self.model_id != "runwayml/stable-diffusion-v1-5":
                # Automatic fallback for unstable/high-memory model loads.
                self.model_id = "runwayml/stable-diffusion-v1-5"
                self.width = min(self.width, 768)
                self.height = min(self.height, 432)
                self.num_inference_steps = min(self.num_inference_steps, 12)
                try:
                    self.pipeline = StableDiffusionPipeline.from_pretrained(
                        self.model_id,
                        torch_dtype=self._pipeline_dtype(),
                        use_safetensors=True,
                    )
                    self.pipeline = self._configure_pipeline(self.pipeline)
                    return
                except Exception as fallback_error:
                    raise RuntimeError(
                        f"Failed to load diffusion model {self.model_id}: {fallback_error}"
                    ) from fallback_error
            raise RuntimeError(f"Failed to load diffusion model {self.model_id}: {e}") from e

    def generate(
        self,
        prompt: str,
        seed: int,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[object, dict]:
        """Generate image via diffusion and return PIL image + metadata."""
        with self._generation_lock:
            if self.pipeline is None:
                self.warm_up()

            # Ensure seed is valid for torch
            seed_int = int(seed) % (2**32)
            generator = torch.Generator(device=self._generator_device()).manual_seed(seed_int)
            target_width = width or self.width
            target_height = height or self.height

            try:
                generation_kwargs = {
                    "prompt": self._trim_prompt(prompt),
                    "height": target_height,
                    "width": target_width,
                    "num_inference_steps": self.num_inference_steps,
                    "guidance_scale": self.guidance_scale,
                    "generator": generator,
                }
                if negative_prompt:
                    generation_kwargs["negative_prompt"] = negative_prompt
                image = self.pipeline(**generation_kwargs).images[0]

                metadata = {
                    "model": self.model_id,
                    "device": self.device,
                    "generator_device": self._generator_device(),
                    "gpu_memory_gb": self.gpu_memory_gb,
                    "steps": self.num_inference_steps,
                    "guidance_scale": self.guidance_scale,
                    "seed": seed_int,
                    "width": target_width,
                    "height": target_height,
                }
                return image, metadata
            except Exception as e:
                # Quality-first run failed. On low-VRAM systems, retry once with a safer
                # profile before bubbling up so we don't crash the request path.
                if self.low_vram_mode:
                    message = str(e).lower()
                    if ("out of memory" in message or "cuda" in message or "device" in message) and (
                        target_width > 768 or target_height > 432 or self.num_inference_steps > 12
                    ):
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        retry_steps = min(self.num_inference_steps, 12)
                        retry_kwargs = {
                            "prompt": self._trim_prompt(prompt),
                            "height": min(target_height, 432),
                            "width": min(target_width, 768),
                            "num_inference_steps": retry_steps,
                            "guidance_scale": self.guidance_scale,
                            "generator": torch.Generator(device=self._generator_device()).manual_seed(seed_int),
                        }
                        if negative_prompt:
                            retry_kwargs["negative_prompt"] = negative_prompt
                        retry_image = self.pipeline(**retry_kwargs).images[0]
                        retry_metadata = {
                            "model": self.model_id,
                            "device": self.device,
                            "generator_device": self._generator_device(),
                            "gpu_memory_gb": self.gpu_memory_gb,
                            "steps": retry_steps,
                            "guidance_scale": self.guidance_scale,
                            "seed": seed_int,
                            "width": retry_kwargs["width"],
                            "height": retry_kwargs["height"],
                            "retry_profile": "low_vram_fallback",
                        }
                        return retry_image, retry_metadata
                raise RuntimeError(f"Diffusion generation failed: {e}")


def get_generator() -> DiffusionGenerator:
    """Singleton accessor for diffusion generator."""
    return DiffusionGenerator()
