<template>
  <div
    class="circular-button no-select"
    :data-testid="$attrs['data-testid'] || 'ui-circular-button-root'"
    :data-capture-ready="captureReadyForUi"
  >
    <svg
      v-bind="$attrs"
      @touchstart.prevent="handleMouseDown($event)" @touchend.prevent="handleMouseUp($event)"
      @mousedown="handleMouseDown($event)" @mouseup="handleMouseUp($event)"
      @mouseleave="clearPress" @touchcancel="clearPress"
      :aria-label="captureActionLabel"
      :data-capture-state="cancelPending ? 'stopping' : (canAbortCapture ? 'capturing' : 'idle')"
      :width="svgSize"
      :height="svgSize"
      :viewBox="'0 0 ' + svgSize + ' ' + svgSize"
      style="cursor: pointer;"
     data-testid="ui-components-circular-button-act-handle-mouse-down">
      <title>{{ captureActionLabel }}</title>
      <!-- 背景圆圈 -->
      <circle
        :cx="svgSize / 2"
        :cy="svgSize / 2"
        :r="radius"
        fill="none"
        stroke="rgba(255, 255, 255, 0.5)"
        :stroke-width="strokeWidth"
      />
      <!-- 红色进度条（长按时显示） -->
       <circle
        v-if="isLongPress"
        :cx="svgSize / 2"
        :cy="svgSize / 2"
        :r="radius"
        fill="none"
        stroke="rgba(255, 0, 0, 0.7)"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="circumference * (1 - longPressProgress)"
        stroke-linecap="round"
        :transform="'rotate(-90 ' + svgSize / 2 + ' ' + svgSize / 2 + ')'"
      />
      <!-- 失败动画：红色闪烁圆环 -->
      <circle
        v-if="isFailed"
        :key="failPulseKey"
        class="failure-ring"
        :cx="svgSize / 2"
        :cy="svgSize / 2"
        :r="radius"
        fill="none"
        stroke="rgba(255, 0, 0, 0.9)"
        :stroke-width="strokeWidth"
      />
      <!-- 进度条 -->
      <circle
        :cx="svgSize / 2"
        :cy="svgSize / 2"
        :r="radius"
        fill="none"
        stroke="rgba(0, 255, 0, 0.7)"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="circumference * (1 - progress)"
        stroke-linecap="round"
        :transform="'rotate(-90 ' + svgSize / 2 + ' ' + svgSize / 2 + ')'"
      />
      <!-- 按钮文本 -->
      <text
        :x="svgSize / 2"
        :y="svgSize / 2 - (canAbortCapture ? 5 : 0)"
        fill="rgba(255, 255, 255, 0.7)"
        :font-size="fontSize"
        text-anchor="middle"
        alignment-baseline="central"
      >
        {{ progressText }}
      </text>
      <text v-if="canAbortCapture" :x="svgSize / 2" :y="svgSize / 2 + 10"
        fill="white" :font-size="fontSize" text-anchor="middle">
        {{ $t('Capture stop label') }}
      </text>

      <image
        :x="svgSize / 2" 
        :y="svgSize / 2"
        v-if="!isClicked"
        xlink:href="@/assets/images/svg/ui/media record.svg"
        width="20px" height="20px"
        style="transform: translate(-8px, -10px);"
      />

    </svg>
  </div>
</template>

<script>
export default {
  inheritAttrs: false,
  data() {
    return {
      progress: 0,
      // circumference: 339.292,
      radius: 30, // 圆的半径
      strokeWidth: 7, // 圆环的线宽
      CaptureExpTime: 1,
      animationDuration: 1, // 动画时长为1000毫秒（1秒）
      animationStartTime: 0, // 动画开始时间
      isClicked: false,

      longPressThreshold: 1000,
      mousePressTimestamp: 0,
      pressAction: '',
      cancelPending: false,
      cancelTimer: null,
      completionTimer: null,

      isLongPress: false,
      longPressProgress: 0,

      MainCameraConnect: false,
      isProcessing: false, // 新增状态变量，表示是否正在处理

      isButtonDisabled: false, // 拍摄按钮是否禁用

      // QHYCCD SDK 主相机采集模式：由 App.vue 的配置项驱动
      captureMode: 'Single', // 'Single' | 'Live' | 'Burst'
      burstFrames: 20,

      // 曝光失败动画
      isFailed: false,
      failPulseKey: 0,
      failTimer: null,

      // 触屏设备上会在 touch 后合成触发一套 mouse 事件，需做去重避免误判长按
      isTouching: false,
      lastTouchTs: 0,
      touchMouseDedupWindowMs: 800,
    };
  },
  created() {
    this.$bus.$on('ExposureCompleted', this.overProgress);
    this.$bus.$on('ExposureFailed', this.onExposureFailed);
    this.$bus.$on('SetExpTime',this.SetDuration);
    this.$bus.$on('CameraInExposuring',this.setInProgress);
    this.$bus.$on('MainCameraConnected', this.MainCameraConnected);
    this.$bus.$on('disableCaptureButton', this.disableCaptureButton);
    this.$bus.$on('SetCaptureMode', (m) => { this.captureMode = String(m || 'Single'); });
    this.$bus.$on('SetBurstFrames', (n) => {
      const v = parseInt(n, 10);
      this.burstFrames = Number.isFinite(v) && !isNaN(v) ? v : 20;
    });
  },
  mounted() {
    this.$bus.$emit('AppSendMessage', 'Vue_Command', 'getCaptureStatus');
  },
  computed: {
    svgSize() {
      // SVG的大小应该足够包含圆形按钮及其边框
      return this.radius * 2 + this.strokeWidth * 2;
    },
    circumference() {
      // 计算圆周长
      return 2 * Math.PI * this.radius;
    },
    canAbortCapture() {
      return this.isClicked && this.progress < 1 && !this.cancelPending;
    },
    captureActionLabel() {
      if (this.cancelPending) return this.$t('Stopping exposure');
      return this.$t(this.canAbortCapture ? 'Stop this exposure' : 'Start exposure');
    },
    progressText() {
      if (this.cancelPending) return this.$t('Capture stopping label');
      if (this.isFailed) return '!';
      return this.isClicked ? `${(this.progress * 100).toFixed(0)}%` : '';
    },
    fontSize() {
      // 字体大小可以根据按钮的大小动态计算
      return this.radius / 3; // 示例比例
    },
    /** 与 `animateProgress` 中 `if (this.isClicked) return` 对齐，供 E2E 在连拍前等待可再次触发拍摄 */
    captureReadyForUi() {
      if (this.isButtonDisabled) return 'false';
      if (this.isClicked) return 'false';
      if (this.isLongPress) return 'false';
      return 'true';
    },
  },
  methods: {
    handleMouseDown(event) {
      // touch/mouse 去重：触摸后短时间内忽略合成的 mouse 事件
      if (event && event.type === 'touchstart') {
        this.isTouching = true;
        this.lastTouchTs = Date.now();
      } else if (event && event.type === 'mousedown') {
        if (this.lastTouchTs && (Date.now() - this.lastTouchTs) < this.touchMouseDedupWindowMs) {
          return;
        }
      }

      if (this.isButtonDisabled) {
        this.$canUseDevice('MainCamera', 'Capture');
        return;
      }
      if (this.cancelPending || (this.isClicked && !this.canAbortCapture)) return;
      this.mousePressTimestamp = Date.now();
      this.pressAction = this.canAbortCapture ? 'stop' : 'start';
      if (this.pressAction === 'stop') this.startLongPressAnimation();
    },

    handleMouseUp(event) {
      // touch/mouse 去重：触摸后短时间内忽略合成的 mouse 事件
      if (event && event.type === 'touchend') {
        this.isTouching = false;
        this.lastTouchTs = Date.now();
      } else if (event && event.type === 'mouseup') {
        if (this.lastTouchTs && (Date.now() - this.lastTouchTs) < this.touchMouseDedupWindowMs) {
          return;
        }
      }

      const action = this.pressAction;
      const elapsed = Date.now() - this.mousePressTimestamp;
      this.clearPress();
      if (this.isButtonDisabled || !action || elapsed >= this.longPressThreshold) return;
      if (action === 'stop') {
        this.cancelCapture();
        return;
      }
      if (!this.MainCameraConnect) {
        this.$bus.$emit('showMsgBox', 'Please connect the camera first.', 'error');
        return;
      }
      if (!this.$store.getters['device/isDeviceBound']('MainCamera')) {
        this.$bus.$emit(
          'showMsgBox',
          this.$t('MainCameraNotBoundAction', { action: this.$t('Feature_Capture') }),
          'error'
        );
        return;
      }
      if (this.$canUseDevice('MainCamera', 'Capture').allowed) this.animateProgress();
    },

    clearPress() {
      this.pressAction = '';
      this.mousePressTimestamp = 0;
      cancelAnimationFrame(this.longPressAnimationRequest);
      this.isLongPress = false;
      this.longPressProgress = 0;
    },

    cancelCapture() {
      if (!this.canAbortCapture) return;
      this.clearPress();
      cancelAnimationFrame(this.animationRequest);
      this.cancelPending = true;
      this.cancelTimer = setTimeout(() => {
        this.cancelPending = false;
        this.$bus.$emit('showMsgBox', this.$t('Exposure stop was not confirmed. Tap again to retry.'), 'warning');
      }, 5000);
      this.$bus.$emit('AppSendMessage', 'Vue_Command', 'abortExposure');
    },

    animateProgress() {
      if (this.isClicked) return; // 如果已点击，则退出方法
      console.log('执行点按，触发拍摄');
      const mode = String(this.captureMode || 'Single');
      if (mode === 'Live') {
        // Live 是预览连续取帧：不触发 takeExposure，否则会把后端模式切回 Single
        this.$bus.$emit('SendConsoleLogMsg', this.$t('LiveModeCaptureHint'), 'info');
        this.$bus.$emit('showMsgBox', this.$t('LiveModeCaptureHint'), 'info');
        return;
      }

      this.animationDuration = this.CaptureExpTime;
      const traceId = `cap_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      this.$bus.$emit('CaptureTraceStart', {
        traceId,
        mode,
        exposureMs: this.animationDuration,
        burstFrames: mode === 'Burst'
          ? Math.max(1, Math.min(1024, parseInt(this.burstFrames, 10) || 20))
          : 1,
      });
      this.$startFeature(['MainCamera'], 'Capture')
      if (mode === 'Burst') {
        const frames = Math.max(1, Math.min(1024, parseInt(this.burstFrames, 10) || 20));
        this.$bus.$emit('AppSendMessage', 'Vue_Command', 'takeExposureBurst:' + this.animationDuration + ':' + frames + ':' + traceId);
        this.$bus.$emit('SendConsoleLogMsg', 'Take Exposure (Burst):' + this.animationDuration + 'ms x' + frames, 'info');
      } else {
        this.$bus.$emit('AppSendMessage', 'Vue_Command', 'takeExposure:' + this.animationDuration + ':' + traceId);
        this.$bus.$emit('SendConsoleLogMsg', 'Take Exposure:' + this.animationDuration, 'info');
      }
      this.isClicked = true;
      const startTime = performance.now();
      const animate = (currentTime) => {
        const elapsedTime = currentTime - startTime;
        this.progress = elapsedTime / (this.animationDuration / 0.99);

        if (this.progress < 0.99) {
          this.animationRequest = requestAnimationFrame(animate);
        } else {
          this.progress = 0.99;
          cancelAnimationFrame(this.animationRequest);
        }
      };
      if (this.animationRequest) {
        cancelAnimationFrame(this.animationRequest);
      }
      this.animationRequest = requestAnimationFrame(animate);
    },

    overProgress() {
      if (!this.isClicked || this.cancelPending) return;
      this.progress = 1;
      cancelAnimationFrame(this.animationRequest);
      this.$stopFeature(['MainCamera'], 'Capture');
      clearTimeout(this.completionTimer);
      this.completionTimer = setTimeout(this.resetProgress, 500);
    },

    onExposureFailed() {
      this.resetProgress();
      this.$stopFeature(['MainCamera'], 'Capture');

      this.isFailed = true;
      this.failPulseKey += 1;
      if (this.failTimer) clearTimeout(this.failTimer);
      this.failTimer = setTimeout(() => {
        this.isFailed = false;
      }, 2000);
    },

    resetProgress() {
      cancelAnimationFrame(this.animationRequest);
      clearTimeout(this.cancelTimer);
      clearTimeout(this.completionTimer);
      this.clearPress();
      this.cancelPending = false;
      this.progress = 0;
      this.isClicked = false;
    },

    SetDuration(time) {
      this.CaptureExpTime = time;
    },

    startLongPressAnimation() {
      console.log('执行长按，触发终止拍摄');
      this.isLongPress = true;
      const startTime = performance.now();
      const animate = (currentTime) => {
        const elapsedTime = currentTime - startTime;
        this.longPressProgress = elapsedTime / this.longPressThreshold;

        if (this.longPressProgress < 1) {
          this.longPressAnimationRequest = requestAnimationFrame(animate);
        } else {
          this.cancelCapture();
        }
      };

      this.longPressAnimationRequest = requestAnimationFrame(animate);
    },

    setInProgress(state) {
      if (state === 'True') {
        if (this.cancelPending) return;
        this.progress = 0.99;
        this.isClicked = true;
      } else {
        this.resetProgress();
      }
    },

    MainCameraConnected(num) {
      if(num === 0){
        this.MainCameraConnect = false;
      } else {
        this.MainCameraConnect = true;
      }
      console.log('MainCamera is Connected: ', num);
    },

    disableCaptureButton(status) {
      this.isButtonDisabled = status;
    },

  },
};
</script>

<style scoped>
.circular-button {
  display: flex;
  justify-content: center;
  align-items: center;
}

.failure-ring {
  animation: failurePulse 0.6s ease-in-out 0s 3;
}

@keyframes failurePulse {
  0% { opacity: 0.2; }
  50% { opacity: 1; }
  100% { opacity: 0.2; }
}

</style>

