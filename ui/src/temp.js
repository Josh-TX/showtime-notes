<script>
  new Vue({
    el: '#app',
    computed: {
      fftSize() {
        return Math.pow(2, this.fftSizeInPow)
      }
    },
    data: function () {
      return {
        showControl: false,
        linear: false,
        log: true,
        played: false,
        myChart: null,
        myChart2: null,
        option: {},
        fData: [],
        fData_log: [],
        fftSizeInPow: 12,
        hue: 0,
        smoothLine: true
      }
    },
    mounted: function () {
      let _ = this
      window.addEventListener('resize', function () {
        _.myChart.resize()
      })
      _.myChart = echarts.init(document.getElementById('main'))
      _.option = {
        animation: false,
        color: ['#4ade80', '#818cf8'],
        grid: {
          top: '0%',
          left: '0%',
          right: '0%',
          bottom: '0%'
        },
        legend: {
          show: false
        },
        xAxis: {
          type: 'category',
          axisLine: {
            show: false
          },
          axisTick: {
            show: false
          },
          axisLabel: {
            show: false
          },
          splitLine: {
            show: false
          }
        },
        yAxis: {
          type: 'value',
          axisLine: {
            show: false
          },
          axisLabel: {
            show: false
          },
          splitLine: {
            show: false
          },
          max: 255,
          min: 0
        },
        series: [
          {
            type: 'line',
            data: [],
            name: 'Signal Level Fixed',
            symbol: 'none',
            lineStyle: {
              width: 1,
              color: '#75CAE0'
            }
          }
        ]
      }
      _.myChart.setOption(_.option)
    },
    methods: {
      play() {
        let _ = this
        if (_.played) {
          return false
        }
        let audio = document.getElementById('music')

        let audioContext = new AudioContext()
        let audioSrc = audioContext.createMediaElementSource(audio)
        let analyzer = audioContext.createAnalyser()

        audioSrc.connect(analyzer)
        analyzer.connect(audioContext.destination)

        setInterval(() => {
          analyzer.fftSize = _.fftSize
          let bufferLength = analyzer.frequencyBinCount
          let frequencyData = new Uint8Array(bufferLength)
          analyzer.getByteFrequencyData(frequencyData)
          _.fData = _.uint8ArrayToArray(frequencyData)

          if (_.log) {
            _.fData = _.logScale(_.fData)
          }

          if (_.smoothLine) {
            _.fData = _.interpolate(_.fData)
          }

          _.option.series[0].data = _.fData
          _.myChart.setOption(_.option)
        }, 1000 / 60)

        _.played = true
      },
      logScale(data) {
        let temp = []
        let length = data.length
        let maxLog = Math.log(length)
        let step = maxLog / length

        for (let i = 0; i < length; i++) {
          let dataIndex = Math.floor(Math.exp(step * i))
          temp.push(data[dataIndex])
        }

        return temp
      },
      easeInOutSine(x) {
        return -(Math.cos(Math.PI * x) - 1) / 2
      },
      interpolate(data, easing = this.easeInOutSine) {
        let halfwayPoint = Math.floor(data.length / 4)
        let firstHalf = data.slice(0, halfwayPoint * 3)
        let secondHalf = data.slice(halfwayPoint * 3)

        let output = []
        let group = [firstHalf[0]]

        for (let i = 1; i < firstHalf.length; i++) {
          if (firstHalf[i] !== group[0]) {
            // If all elements in the group equal 0, simply add them to the output array
            if (group[0] === 0) {
              output.push(...group)
            } else {
              // Calculate the step according the count of same-number elements
              let step = 1 / group.length
              let difference = firstHalf[i] - group[0]

              // Populate the output array
              for (let j = 0; j < group.length; j++) {
                // Apply the easing function to the interpolated value
                let value = group[0] + difference * easing(step * j)
                output.push(value)
              }
            }

            group = [firstHalf[i]] // Reset the group
          } else {
            group.push(firstHalf[i])
          }
        }

        // Process the final group
        for (let j = 0; j < group.length; j++) {
          let value = group[0]
          output.push(value)
        }

        // Combine the processed first half and the original second half
        return [...output, ...secondHalf]
      },
      uint8ArrayToArray(uint8Array) {
        let array = []

        for (let i = 0; i < uint8Array.byteLength; i++) {
          array[i] = uint8Array[i]
        }

        return array
      },
      dropData(data) {
        let drop_index = Math.floor(data.length * 0.334) // 0.171
        data.splice(data.length - drop_index, drop_index - 1)
        return data
      },
      cutArray(data) {
        let index = Math.floor(data.length / 3)

        return data.splice(5, index)
      }
    }
  })
</script>