import React from 'react';
import ReactDOM from 'react-dom';


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
          <Row label="Sorting started"  value={this.state.startDate} />
          <Row label="Sorting finished" value={this.state.endDate} />
          <Row label="Sequence length"  value={this.state.sequenceLength} />
          <Row label="Current speed"    value={this.state.currentSpeed + " shuffles per second"} />
        </table>
      </div>
    );
  }
}


function Row(props) {
  return (
    <tr>
      <td>props.label</td>
      <td>props.value</td>
    </tr>
  );
}


ReactDOM.render(
  <Statistics />,
  document.getElementById('react-root')
);
