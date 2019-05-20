import * as R from 'ramda'
import * as React from 'react'
import { Link } from 'react-router-dom'
import {
  Card,
  CardContent,
  CircularProgress,
  Typography,
  colors,
} from '@material-ui/core'
import { unstable_Box as Box } from '@material-ui/core/Box'
import { makeStyles, withStyles } from '@material-ui/styles'

import Sparkline from 'components/Sparkline'
import AsyncResult from 'utils/AsyncResult'
import * as AWS from 'utils/AWS'
import * as Config from 'utils/Config'
import Data from 'utils/Data'
import * as NamedRoutes from 'utils/NamedRoutes'
import * as RT from 'utils/reactTools'

import { displayError } from './errors'
import * as requests from './requests'

const Field = RT.composeComponent(
  'Bucket.PackageDetail.Field',
  withStyles(({ typography }) => ({
    root: {
      display: 'flex',
    },
    label: {
      fontWeight: typography.fontWeightMedium,
      width: 80,
    },
    value: {},
  })),
  ({ classes, label, children }) => (
    <Typography variant="body1" className={classes.root}>
      <span className={classes.label}>{label}</span>
      <span className={classes.value}>{children}</span>
    </Typography>
  ),
)

const useStyles = makeStyles(({ spacing: { unit }, palette }) => ({
  card: {
    marginTop: unit,
  },
  link: {
    display: 'block',
    '&:hover': {
      background: palette.action.hover,
    },
  },
}))

export default ({
  match: {
    params: { bucket, name },
  },
}) => {
  const { urls } = NamedRoutes.use()
  const classes = useStyles()
  const s3 = AWS.S3.use()
  const signer = AWS.Signer.use()
  const { apiGatewayEndpoint: endpoint, analyticsBucket } = Config.useConfig()
  const today = React.useMemo(() => new Date(), [])
  return (
    <>
      <Typography variant="h4">{name}: revisions</Typography>
      <Data
        fetch={requests.getPackageRevisions}
        params={{ s3, signer, endpoint, bucket, name }}
      >
        {AsyncResult.case({
          _: () => <CircularProgress />,
          Err: displayError(),
          Ok: R.map(
            ({ id, hash, modified, info }) =>
              id !== 'latest' && (
                <Card key={id} className={classes.card}>
                  <CardContent
                    component={Link}
                    className={classes.link}
                    to={urls.bucketPackageTree(bucket, name, id)}
                  >
                    <Box
                      display="flex"
                      flexWrap="wrap"
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Box>
                        <Field label="Message:">{info.commit_message || '<empty>'}</Field>
                        <Field label="Date:">{modified.toLocaleString()}</Field>
                        <Field label="Hash:">{hash}</Field>
                      </Box>
                      <Data
                        fetch={requests.pkgStats}
                        params={{ s3, analyticsBucket, bucket, name, hash, today }}
                      >
                        {AsyncResult.case({
                          Ok: ({ counts, total }) => (
                            <Box minWidth={300} mt={3} ml={10}>
                              <Sparkline
                                data={R.pluck('value', counts)}
                                width={300}
                                height={20}
                                color={colors.blueGrey[100]}
                                color2={colors.blueGrey[800]}
                                fill={false}
                              />
                            </Box>
                          ),
                          Pending: () => <CircularProgress />,
                          _: () => null,
                        })}
                      </Data>
                    </Box>
                  </CardContent>
                </Card>
              ),
          ),
        })}
      </Data>
    </>
  )
}
