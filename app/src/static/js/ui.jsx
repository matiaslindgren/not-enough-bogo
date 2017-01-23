class Statistics extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      startDate:      "Loading...",
      endDate:        "Loading...",
      sequenceLength: "Loading...",
      currentSpeed:   "Loading...",
    };
  }

  componentDidMount() {
    this.timerID = setInterval(_ => this.refreshState(), 1000);
  }

  componentWillUnmount() {
    clearInterval(this.timerID);
  }

  refreshState() {
    this.setState({
      startDate:      "TODO",
      endDate:        "TODO",
      sequenceLength: "TODO",
      currentSpeed:   "TODO",
    });
  }

  render() {
    return (
      <div>
        <table class="table table-condensed">
          <tr>
            <td>Sorting started</td>
            <td>{this.state.startDate}</td>
          </tr>
          <tr>
            <td>Sorting finished</td>
            <td>{this.state.endDate}</td>
          </tr>
          <tr>
            <td>Sequence length</td>
            <td>{this.state.sequenceLength}</td>
          </tr>
          <tr>
            <td>Current speed</td>
            <td>{this.state.currentSpeed} shuffles per second</td>
          </tr>
        </table>
      </div>
    );
  }
}

ReactDOM.render(
  <Statistics />,
  document.getElementById('react-root')
);
