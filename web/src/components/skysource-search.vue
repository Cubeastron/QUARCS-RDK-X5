// Stellarium Web - Copyright (c) 2022 - Stellarium Labs SRL
//
// This program is licensed under the terms of the GNU AGPL v3, or
// alternatively under a commercial licence.
//
// The terms of the AGPL v3 license can be found in the main directory of this
// repository.

<template>
  <div style="position: relative;" v-click-outside="resetSearch" data-testid="ui-skysource-search-root">
    <v-text-field ref="searchField" prepend-icon="mdi-magnify" :label="$t('Search...')" v-model="searchText" @keyup.native.esc="resetSearch()" hide-details single-line data-testid="ui-skysource-search-input-search-field"></v-text-field>
    <v-list dense v-if="showList" two-line :style="listStyle">
      <v-list-item v-for="source in autoCompleteChoices" :key="source.names[0]" @click="sourceClicked(source)" data-testid="ui-components-skysource-search-act-source-clicked">
        <v-list-item-action>
          <img :src="iconForSkySource(source)"/>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>{{ nameForSkySource(source) }}</v-list-item-title>
          <v-list-item-subtitle>{{ typeToName(source.types[0]) }}</v-list-item-subtitle>
          <v-list-item-subtitle>{{ radecForSkySource(source) }}</v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </div>
</template>

<script>
import swh from '@/assets/sw_helpers.js'
import { localizedSkySourceName, localizedSkySourceType } from '@/assets/sky-localization'
import vClickOutside from 'v-click-outside'
import _ from 'lodash'

export default {
  data: function () {
    return {
      autoCompleteChoices: [],
      searchText: '',
      lastQuery: undefined,
    }
  },
  props: ['value', 'floatingList'],
  watch: {
    searchText: function () {
      if (this.searchText === '') {
        this.autoCompleteChoices = []
        this.lastQuery = undefined
        return
      }
      this.refresh()
    }
  },
  computed: {
    listStyle: function () {
      return this.floatingList ? 'position: absolute; z-index: 300; margin-top: 8px' : ''
    },
    showList: function () {
      return this.searchText !== ''
    }
  },
  created() {
    this.$bus.$on('SearchName',this.SelectedObjectByName);

    // this.$bus.$on('insertObjName',this.SelectedObjectByName);
  },
  methods: {
    SelectedObjectByName(text) {
      swh.querySkySources(text, 10).then(results => {
        const [source] = results
        if (!source) return
        const { ra, de } = source.model_data || {}
        if (Number.isFinite(ra) && Number.isFinite(de)) {
          this.$bus.$emit('TargetRaDec', this.radecForSkySource(source))
        }
        this.sourceClicked(source)
      }, err => { console.log(err) })
    },
    sourceClicked: function (val) {
      this.$emit('input', val)
      this.resetSearch()
    },
    resetSearch: function () {
      this.searchText = ''
    },
    refresh: _.debounce(function () {
      var that = this
      let str = that.searchText
      str = str.toUpperCase()
      str = str.replace(/\s+/g, '')
      // console.log('searchText: ' + that.searchText)
      // console.log('Input search query: ' + str)
      if (this.lastQuery === str) {
        return
      }
      this.lastQuery = str
      swh.querySkySources(str, 10).then(results => {
        if (str !== that.lastQuery) {
          console.log('Cancelled query: ' + str)
          return
        }
        that.autoCompleteChoices = results
        // for (let i = 0; i < that.autoCompleteChoices.length; i++) {
        //   console.log('List[', i, ']:', this.nameForSkySource(that.autoCompleteChoices[i]))
        // }
      }, err => { console.log(err) })
    }, 200),
    nameForSkySource: function (s) {
      const cn = swh.cleanupOneSkySourceName(s.match)
      const n = swh.nameForSkySource(s)
      const localized = localizedSkySourceName(s, this.$i18n.locale)
      if (localized) {
        const identifier = s.names.find(name => /^(M|NGC|IC)\s+\d/.test(name))
        return localized + ' (' + (identifier || n) + ')'
      }
      if (this.$i18n.locale !== 'cn' && /[\u3400-\u9fff]/.test(cn)) return n
      if (cn === n) {
        return n
      } else {
        return cn + ' (' + n + ')'
      }
    },
    radecForSkySource: function (s) {
      let { ra, dec } = swh.radecForSkySource(s)
      return 'Ra:' + ra + ',' + 'Dec:' + dec
    },
    typeToName: function (t) {
      return localizedSkySourceType(t, this.$i18n.locale) || swh.nameForSkySourceType(t)
    },
    iconForSkySource: function (s) {
      return swh.iconForSkySource(s)
    }
  },
  mounted: function () {
    var that = this
    const onClick = e => {
      if (that.searchText !== '') {
        that.searchText = ''
      }
    }
    const guiParent = document.querySelector('stel') || document.body
    guiParent.addEventListener('click', onClick, false)
  },
  directives: {
    clickOutside: vClickOutside.directive
  }
}
</script>

<style>

</style>
