<template>
  <v-dialog :value="true" :fullscreen="$vuetify.breakpoint.xsOnly" max-width="920"
    @input="value => { if (!value) $emit('close') }">
    <v-card data-testid="indi-panel" dark>
      <v-card-title>
        {{ $t('IndiPanel.title') }}
        <v-spacer />
        <v-btn text @click="showStartup = !showStartup">
          {{ $t(showStartup ? 'IndiStartup.devices' : 'IndiStartup.title') }}
        </v-btn>
        <v-btn icon :aria-label="$t('IndiPanel.close')" @click="$emit('close')">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text v-if="showStartup">
        <IndiStartupDrivers />
      </v-card-text>
      <v-card-text v-else>
        <div class="indi-toolbar">
          <v-select v-model="device" :items="devices" item-text="name" item-value="name"
            :label="$t('IndiPanel.device')" dense hide-details @change="selectDevice" data-testid="indi-device">
            <template v-slot:item="{ item }">
              <span>{{ item.name }} · {{ $t(item.connected ? 'IndiPanel.connected' : 'IndiPanel.disconnected') }}</span>
            </template>
          </v-select>
          <v-btn text @click="refresh" data-testid="indi-refresh">{{ $t('IndiPanel.refresh') }}</v-btn>
        </div>
        <v-alert v-if="feedback" dense text :type="feedbackType" class="mt-3" data-testid="indi-feedback">
          {{ $t(feedback) }}
        </v-alert>
        <p v-if="!online" class="mt-4 mb-0">{{ $t('IndiPanel.waiting') }}</p>
        <p v-else-if="!devices.length" class="mt-4 mb-0">{{ $t('IndiPanel.noDevices') }}</p>
        <p v-else-if="!properties.length" class="mt-4 mb-0">{{ $t('IndiPanel.noProperties') }}</p>
        <template v-else>
          <v-tabs v-model="groupIndex" show-arrows background-color="transparent" data-testid="indi-groups">
            <v-tab v-for="group in groups" :key="group">{{ group || $t('IndiPanel.general') }}</v-tab>
          </v-tabs>
          <div class="indi-properties" data-testid="indi-properties">
            <article v-for="property in visibleProperties" :key="property.name"
              class="indi-property" :data-property="property.name">
              <div class="indi-property-heading">
                <div>
                  <strong>{{ property.label || property.name }}</strong>
                  <small v-if="property.label !== property.name">{{ property.name }}</small>
                </div>
                <v-chip small outlined :color="stateColors[property.state] || 'grey'">
                  {{ $te('IndiPanel.state.' + property.state) ? $t('IndiPanel.state.' + property.state) : property.state }}
                </v-chip>
              </div>
              <div class="indi-fields">
                <label v-for="element in property.elements" :key="element.name" class="indi-field">
                  <template v-if="property.type === 'switch'">
                    <input :type="property.rule === 'one' ? 'radio' : 'checkbox'" :name="property.name"
                      :data-element="element.name" :checked="!!valueOf(property, element)" :disabled="!property.writable || isWriting(property)"
                      @change="setSwitch(property, element, $event.target.checked)" />
                    <span>{{ element.label || element.name }}</span>
                  </template>
                  <template v-else>
                    <span>{{ element.label || element.name }}</span>
                    <input v-if="property.writable" class="indi-input" :data-element="element.name"
                      :type="property.type === 'number' ? 'number' : 'text'" :value="valueOf(property, element)"
                      :disabled="isWriting(property)"
                      :min="element.max > element.min ? element.min : undefined"
                      :max="element.max > element.min ? element.max : undefined"
                      :step="element.step > 0 ? element.step : 'any'"
                      @input="setDraft(property, { [element.name]: $event.target.value })" />
                    <output v-else>{{ valueOf(property, element) }}</output>
                  </template>
                </label>
              </div>
              <div v-if="property.writable" class="indi-actions">
                <v-btn small text :disabled="!drafts[property.name] || isWriting(property)" @click="$delete(drafts, property.name)">
                  {{ $t('IndiPanel.reset') }}
                </v-btn>
                <v-btn small color="primary" :disabled="!drafts[property.name] || !!writeRequest"
                  @click="apply(property)" data-testid="indi-apply">{{ $t('IndiPanel.apply') }}</v-btn>
              </div>
            </article>
          </div>
        </template>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script>
import IndiStartupDrivers from '@/components/IndiStartupDrivers.vue';

export default {
  components: { IndiStartupDrivers },
  props: { sendCommand: { type: Function, required: true } },
  data() {
    return {
      showStartup: false,
      device: '',
      devices: [],
      properties: [],
      groupIndex: 0,
      online: false,
      drafts: {},
      feedback: '',
      feedbackType: 'info',
      stateColors: { Ok: 'green', Busy: 'amber', Alert: 'red' },
      requestPrefix: Date.now().toString(36) + Math.random().toString(36).slice(2),
      requestSequence: 0,
      stateRequest: '',
      writeRequest: null,
      poll: null,
    };
  },
  computed: {
    groups() { return [...new Set(this.properties.map(property => property.group))]; },
    visibleProperties() { return this.properties.filter(property => property.group === this.groups[this.groupIndex]); },
  },
  mounted() {
    this.refresh();
    this.poll = setInterval(() => {
      if (!this.showStartup) this.refresh();
    }, 1800);
  },
  beforeDestroy() { clearInterval(this.poll); },
  methods: {
    nextRequest() { return this.requestPrefix + '-' + (++this.requestSequence); },
    refresh() {
      if (this.writeRequest && Date.now() > this.writeRequest.deadline) {
        this.writeRequest = null;
        this.feedback = 'IndiPanel.noReply';
        this.feedbackType = 'error';
      }
      this.stateRequest = this.nextRequest();
      this.sendCommand('Vue_Command', 'GetIndiPanel:' + JSON.stringify({ request: this.stateRequest, device: this.device }));
    },
    selectDevice() {
      this.groupIndex = 0;
      this.properties = [];
      this.drafts = {};
      this.feedback = '';
      this.refresh();
    },
    receiveState(state) {
      if (state.request !== this.stateRequest || state.device !== this.device) return;
      this.online = state.online;
      this.devices = state.devices;
      if (!this.devices.some(device => device.name === this.device)) {
        const next = (this.devices.find(device => device.connected) || this.devices[0] || {}).name || '';
        if (this.device !== next) {
          this.device = next;
          this.selectDevice();
        }
        return;
      }
      const group = this.groups[this.groupIndex];
      this.properties = state.properties;
      this.groupIndex = Math.max(0, this.groups.indexOf(group));
    },
    valueOf(property, element) {
      const draft = this.drafts[property.name];
      return draft && Object.prototype.hasOwnProperty.call(draft, element.name) ? draft[element.name] : element.value;
    },
    setDraft(property, changes) {
      this.$set(this.drafts, property.name, { ...this.drafts[property.name], ...changes });
    },
    setSwitch(property, element, checked) {
      if (property.rule === 'any') {
        this.setDraft(property, { [element.name]: checked });
      } else {
        this.setDraft(property, Object.fromEntries(property.elements.map(item => [
          item.name, checked && item.name === element.name,
        ])));
      }
    },
    isWriting(property) {
      return this.writeRequest && this.writeRequest.device === this.device && this.writeRequest.property === property.name;
    },
    apply(property) {
      const draft = this.drafts[property.name];
      let values = draft;
      if (property.type === 'switch') {
        values = Object.fromEntries(property.elements.map(element => [element.name, !!this.valueOf(property, element)]));
      } else if (property.type === 'number') {
        const entries = Object.entries(draft);
        if (entries.some(([, value]) => !String(value).trim() || !Number.isFinite(Number(value)))) {
          this.feedback = 'IndiPanel.invalidNumber';
          this.feedbackType = 'error';
          return;
        }
        values = Object.fromEntries(entries.map(([key, value]) => [key, Number(value)]));
      }
      const request = this.nextRequest();
      this.writeRequest = { request, device: this.device, property: property.name, deadline: Date.now() + 5000 };
      this.feedback = '';
      this.sendCommand('Vue_Command', 'SetIndiPanel:' + JSON.stringify({
        request, device: this.device, property: property.name, values,
      }));
    },
    receiveWrite(response) {
      const pending = this.writeRequest;
      if (!pending || response.request !== pending.request) return;
      this.writeRequest = null;
      if (pending.device !== this.device) return;
      if (response.ok) this.$delete(this.drafts, pending.property);
      this.feedback = response.ok ? 'IndiPanel.sent' : 'IndiPanel.rejected';
      this.feedbackType = response.ok ? 'info' : 'error';
      this.refresh();
    },
  },
};
</script>

<style scoped>
.indi-toolbar, .indi-property-heading, .indi-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.indi-properties {
  max-height: min(58vh, 610px);
  overflow: auto;
}
.indi-property {
  padding: 14px 4px;
  border-bottom: 1px solid rgba(255,255,255,.15);
}
.indi-property-heading { justify-content: space-between; }
.indi-property-heading small { display: block; color: #aaa; overflow-wrap: anywhere; }
.indi-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 8px 16px;
  margin-top: 10px;
}
.indi-field { display: flex; align-items: center; gap: 8px; min-width: 0; overflow-wrap: anywhere; }
.indi-field input[type=checkbox], .indi-field input[type=radio] { accent-color: #42a5f5; flex: none; }
.indi-input {
  min-width: 0;
  width: 100%;
  padding: 4px 6px;
  border: 1px solid #666;
  border-radius: 4px;
}
.indi-field output { color: #ddd; }
.indi-actions { justify-content: flex-end; margin-top: 8px; }
</style>
