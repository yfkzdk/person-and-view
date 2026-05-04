"""
声线模拟集成模块

将 so-vits-svc 声线转换集成到对话系统
流程：文本 → Edge TTS生成基础语音 → so-vits-svc转换成目标声线 → 输出
"""
import asyncio
import os
import subprocess
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# so-vits-svc 路径
SVC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "external", "so-vits-svc-4.1-Stable")
SVC_VENV_PYTHON = os.path.join(SVC_DIR, "venv", "Scripts", "python.exe")
SVC_INFER_SCRIPT = os.path.join(SVC_DIR, "inference_main.py")


class VoiceCloner:
    """声线模拟器 - 基于 so-vits-svc"""

    def __init__(self):
        self.svc_dir = SVC_DIR
        self.python = SVC_VENV_PYTHON
        self.available = self._check_available()

    def _check_available(self) -> bool:
        """检查 so-vits-svc 是否可用"""
        if not os.path.exists(self.python):
            logger.warning("so-vits-svc venv not found")
            return False

        if not os.path.exists(SVC_INFER_SCRIPT):
            logger.warning("so-vits-svc inference script not found")
            return False

        return True

    def check_environment(self) -> dict:
        """检查环境状态"""
        result = {
            "svc_exists": os.path.exists(self.svc_dir),
            "venv_exists": os.path.exists(self.python),
            "pretrain_hubert": os.path.exists(os.path.join(self.svc_dir, "pretrain", "put_hubert_ckpt_here", "hubert_base.pt")),
            "pretrain_hifigan": os.path.exists(os.path.join(self.svc_dir, "pretrain", "nsf_hifigan", "nsf_hifigan_20221211-old2.pth")),
            "trained_models": [],
            "cuda": False,
            "gpu_name": "N/A"
        }

        # 检查训练好的模型
        logs_44k = os.path.join(self.svc_dir, "logs", "44k")
        if os.path.exists(logs_44k):
            for f in os.listdir(logs_44k):
                if f.endswith(".pth") and f.startswith("G_"):
                    result["trained_models"].append(f)

        # 检查 CUDA
        if result["venv_exists"]:
            try:
                out = subprocess.run(
                    [self.python, "-c",
                     "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"],
                    capture_output=True, text=True, timeout=10
                )
                lines = out.stdout.strip().split("\n")
                result["cuda"] = lines[0] == "True"
                result["gpu_name"] = lines[1] if len(lines) > 1 else "N/A"
            except Exception:
                pass

        return result

    def list_trained_models(self) -> list:
        """列出可用的训练模型"""
        models = []
        logs_44k = os.path.join(self.svc_dir, "logs", "44k")
        if os.path.exists(logs_44k):
            for f in os.listdir(logs_44k):
                if f.endswith(".pth") and f.startswith("G_"):
                    models.append({
                        "name": f,
                        "path": os.path.join(logs_44k, f),
                        "config": os.path.join(logs_44k, "config.json")
                    })
        return models

    async def convert_voice(
        self,
        input_wav: str,
        output_path: str,
        model_path: str,
        config_path: str,
        speaker: str = "default",
        transpose: int = 0,
        f0_predictor: str = "pm",
        cluster_ratio: float = 0
    ) -> str:
        """
        声线转换

        Args:
            input_wav: 输入音频路径
            output_path: 输出音频路径
            model_path: 模型路径
            config_path: 配置路径
            speaker: 说话人名称
            transpose: 音高调整（半音）
            f0_predictor: F0预测器 (pm/crepe/dio/harvest/rmvpe)
            cluster_ratio: 聚类占比

        Returns:
            输出音频路径
        """
        if not self.available:
            raise RuntimeError("so-vits-svc not available")

        # 将输入文件复制到 raw 目录
        raw_dir = os.path.join(self.svc_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)

        basename = os.path.basename(input_wav)
        raw_path = os.path.join(raw_dir, basename)

        # 复制文件
        import shutil
        shutil.copy2(input_wav, raw_path)

        # 构建推理命令
        cmd = [
            self.python, SVC_INFER_SCRIPT,
            "-m", model_path,
            "-c", config_path,
            "-n", basename.replace(".wav", ""),
            "-t", str(transpose),
            "-s", speaker,
            "-f0p", f0_predictor,
            "-cr", str(cluster_ratio),
            "-wf", "wav"
        ]

        logger.info(f"Running voice conversion: {' '.join(cmd)}")

        # 执行推理
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.svc_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Voice conversion failed: {stderr.decode()}")
            raise RuntimeError(f"Voice conversion failed: {stderr.decode()}")

        # 查找输出文件
        results_dir = os.path.join(self.svc_dir, "results")
        output_file = None
        for f in os.listdir(results_dir):
            if basename.replace(".wav", "") in f and f.endswith(".wav"):
                output_file = os.path.join(results_dir, f)
                break

        if output_file and output_path:
            shutil.move(output_file, output_path)
            return output_path

        return output_file or ""

    async def text_to_voice(
        self,
        text: str,
        output_path: str,
        model_path: str,
        config_path: str,
        speaker: str = "default",
        base_voice: str = "zh-CN-YunxiNeural",
        transpose: int = 0
    ) -> str:
        """
        文本 → 基础语音 → 声线转换

        Args:
            text: 要合成的文本
            output_path: 最终输出路径
            model_path: so-vits-svc 模型路径
            config_path: so-vits-svc 配置路径
            speaker: 目标说话人
            base_voice: Edge TTS 基础声音
            transpose: 音高调整

        Returns:
            输出音频路径
        """
        # 1. Edge TTS 生成基础语音
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            base_wav = f.name

        communicate = edge_tts.Communicate(text, base_voice)
        await communicate.save(base_wav)

        logger.info(f"Base TTS generated: {base_wav}")

        # 2. so-vits-svc 声线转换
        result = await self.convert_voice(
            input_wav=base_wav,
            output_path=output_path,
            model_path=model_path,
            config_path=config_path,
            speaker=speaker,
            transpose=transpose
        )

        # 清理临时文件
        os.unlink(base_wav)

        return result


def print_environment_status():
    """打印环境状态"""
    cloner = VoiceCloner()
    env = cloner.check_environment()

    print("=" * 60)
    print("so-vits-svc 声线模拟环境状态")
    print("=" * 60)
    print(f"  项目目录: {'✅' if env['svc_exists'] else '❌'}")
    print(f"  Python虚拟环境: {'✅' if env['venv_exists'] else '❌'}")
    print(f"  CUDA支持: {'✅' if env['cuda'] else '❌'} ({env['gpu_name']})")
    print(f"  Hubert预训练模型: {'✅' if env['pretrain_hubert'] else '❌ (需要下载)'}")
    print(f"  NSF-HiFiGAN预训练模型: {'✅' if env['pretrain_hifigan'] else '❌ (需要下载)'}")
    print(f"  训练好的声线模型: {len(env['trained_models'])} 个")
    for m in env['trained_models']:
        print(f"    - {m}")

    if not env['trained_models']:
        print("\n  ⚠️ 没有训练好的声线模型")
        print("  需要提供录音样本来训练，步骤：")
        print("  1. 将录音放入 dataset_raw/ 目录")
        print("  2. 运行预处理: python resample.py")
        print("  3. 运行训练: python train.py")
        print("  4. 训练完成后即可推理")

    print("=" * 60)

    return env


if __name__ == "__main__":
    print_environment_status()
