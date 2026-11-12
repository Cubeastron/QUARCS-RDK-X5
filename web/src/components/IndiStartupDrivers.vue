<template>
  <section>
    <h3>{{ $t('IndiStartup.title') }}</h3>
    <v-alert v-if="feedback" dense text :type="feedbackType" class="mt-3">
      {{ $t('IndiStartup.' + feedback) }}
    </v-alert>
    <v-simple-table v-if="drivers.length">
      <template v-slot:default>
        <thead>
          <tr>
            <th scope="col">{{ $t('IndiStartup.driver') }}</th>
            <th scope="col">{{ $t('IndiStartup.load') }}</th>
            <th scope="col">{{ $t('IndiStartup.running') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="driver in drivers" :key="driver.id">
            <td>
              <label :for="'indi-startup-' + driver.id">{{ $t('IndiStartup.driverNames.' + driver.id) }}</label>
              <small class="d-block">{{ driver.executable }}</small>
            </td>
            <td>
              <input :id="'indi-startup-' + driver.id" v-model="selected" :value="driver.id"
                type="checkbox" :disabled="!!busy || !driver.available">
              <small v-if="!driver.available" class="d-block">{{ $t('IndiStartup.unavailable') }}</small>
            </td>
            <td>{{ $t(running.includes(driver.id) ? 'IndiStartup.loaded' : 'IndiStartup.unloaded') }}</td>
          </tr>
        </tbody>
      </template>
    </v-simple-table>
    <p v-if="pending" class="mt-3 mb-1">{{ $t('IndiStartup.pending') }}</p>
    <p v-if="drivers.length" class="mt-3">{{ $t('IndiStartup.restartHint') }}</p>
    <div class="d-flex flex-wrap justify-end">
      <v-btn text class="ma-1" :disabled="!!busy" @click="request('refresh')">{{ $t('IndiPanel.refresh') }}</v-btn>
      <v-btn outlined class="ma-1" :disabled="!!busy || !dirty || !selected.length"
        :loading="busy === 'save'" @click="request('save')">{{ $t('IndiStartup.save') }}</v-btn>
      <v-btn color="primary" class="ma-1" :disabled="!!busy || dirty || !pending"
        :loading="busy === 'restart'" @click="request('restart')">{{ $t('IndiStartup.restart') }}</v-btn>
    </div>
  </section>
</template>

<script>
const api = '/api/indi-startup';

function sameDrivers(left, right) {
  return left.length === right.length && left.every(driver => right.includes(driver));
}

export default {
  data() {
    return { drivers: [], selected: [], saved: [], running: [], busy: '', feedback: '', feedbackType: 'info' };
  },
  computed: {
    dirty() { return !sameDrivers(this.selected, this.saved); },
    pending() { return !sameDrivers(this.saved, this.running); },
  },
  mounted() { this.request('refresh'); },
  methods: {
    async request(action) {
      this.busy = action;
      this.feedback = '';
      try {
        const url = action === 'restart' ? api + '/restart' : api;
        const options = action === 'refresh' ? { cache: 'no-store' } : {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(action === 'save' ? { drivers: this.selected } : {}),
        };
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
          this.feedback = ['invalidDrivers', 'driverUnavailable'].includes(data.error) ? data.error : 'serviceError';
          this.feedbackType = 'error';
          return;
        }
        this.drivers = data.drivers;
        this.selected = [...data.saved];
        this.saved = data.saved;
        this.running = data.running;
        if (action !== 'refresh') {
          this.feedback = action === 'save' ? 'saved' : 'restarted';
          this.feedbackType = 'success';
        }
      } catch {
        this.feedback = 'serviceError';
        this.feedbackType = 'error';
      } finally {
        this.busy = '';
      }
    },
  },
};
</script>
